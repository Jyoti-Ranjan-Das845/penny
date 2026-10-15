"""Exercise real runner event dispatch against a native injection transport."""

from __future__ import annotations

import asyncio
import copy

import pytest

from omnigent.runner import create_runner_app
from omnigent.spec.types import AgentSpec, ExecutorFallback, ExecutorSpec
from tests.runner.conftest import _FakeProcessManager, _runner_client, _ScriptedHarnessClient, _sse
from tests.runner.helpers import NullServerClient


def _spec(primary="model-a", harness="claude-native"):
    return AgentSpec(
        spec_version=1,
        name="reviewer",
        instructions="Keep all citations.",
        executor=ExecutorSpec(
            type="omnigent",
            model=primary,
            reasoning_effort="high",
            config={"harness": harness},
            fallbacks=[
                ExecutorFallback("model-b", "claude-native", "medium"),
                ExecutorFallback("model-c", "codex-native", "xhigh"),
            ],
        ),
    )


async def _settle(predicate):
    for _ in range(200):
        if predicate():
            return
        await asyncio.sleep(0.01)
    assert predicate()


def _failure(harness, external, turn):
    return {
        "type": "native_fallback_claim",
        "data": {
            "status": "failed",
            "expected_external_session_id": external,
            "native_failure": {
                "harness": harness,
                "external_session_id": external,
                "turn_id": turn,
                "kind": "model_unavailable",
                "before_work": True,
            },
        },
    }


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "primary_harness,last_harness",
    [("claude-native", "codex-native"), ("codex-native", "claude-native")],
)
async def test_native_chain_replays_original_input_once_per_backup(
    tmp_path, monkeypatch, primary_harness, last_harness
):
    from omnigent import claude_native_bridge, codex_native_bridge

    monkeypatch.setattr(claude_native_bridge, "_BRIDGE_ROOT", tmp_path / "claude")
    monkeypatch.setattr(codex_native_bridge, "_BRIDGE_ROOT", tmp_path / "codex")
    original = _spec(harness=primary_harness)
    original.executor.fallbacks[1] = ExecutorFallback("model-c", last_harness, "xhigh")

    async def resolve(*_):
        return original

    hc = _ScriptedHarnessClient(
        [
            _sse({"type": "response.created", "response": {"id": "r1"}}),
            _sse({"type": "response.completed", "response": {"id": "r1"}}),
        ]
    )
    pm = _FakeProcessManager(hc)
    app = create_runner_app(
        process_manager=pm, spec_resolver=resolve, server_client=NullServerClient()
    )
    content = [
        {"type": "input_text", "text": "Review this source exactly."},
        {
            "type": "input_file",
            "filename": "source.txt",
            "file_data": "data:text/plain;base64,c291cmNl",
        },
    ]
    async with _runner_client(app) as client:
        response = await client.post(
            "/v1/sessions/conv_fallback/events",
            json={
                "type": "message",
                "agent_id": "agent_role",
                "pending_input_id": "pending_1",
                "content": content,
                "instructions": "Use the supplied file.",
            },
        )
        assert response.status_code == 202
        await _settle(lambda: len(hc.posted_bodies) == 1)
        await asyncio.sleep(0.02)
        # The native forwarder commits the optimistic user bubble after injection.
        await client.post(
            "/v1/sessions/conv_fallback/events",
            json={
                "type": "native_input_committed",
                "pending_input_id": "pending_1",
                "persisted_item_id": "item_original",
            },
        )
        for index, (harness, model, effort) in enumerate(
            [("claude-native", "model-b", "medium"), (last_harness, "model-c", "xhigh")]
        ):
            source = primary_harness if index == 0 else "claude-native"
            event = _failure(source, f"external_{index}", f"turn_{index}")
            first, duplicate = await asyncio.gather(
                client.post("/v1/sessions/conv_fallback/events", json=event),
                client.post("/v1/sessions/conv_fallback/events", json=copy.deepcopy(event)),
            )
            decision = first.json()["fallback"]
            assert duplicate.json()["fallback"]["attempt_id"] == decision["attempt_id"]
            assert decision["history_before_item_id"] == "item_original"
            started = await client.post(
                "/v1/sessions/conv_fallback/events",
                json={"type": "native_fallback_start", "attempt_id": decision["attempt_id"]},
            )
            assert started.json() == {"started": True}
            await _settle(lambda expected=index + 2: len(hc.posted_bodies) == expected)
            await asyncio.sleep(0.02)
            replay = hc.posted_bodies[-1]
            assert replay["model_override"] == model
            assert replay["reasoning"] == {"effort": effort}
            assert replay["content"] == content
            assert "Keep all citations." in replay["instructions"]
            assert "Use the supplied file." in replay["instructions"]
            assert pm.get_client_calls[-1][1] == harness
            assert (await client.post("/v1/sessions/conv_fallback/events", json=event)).json() == {
                "ignored": True
            }
        exhausted = await client.post(
            "/v1/sessions/conv_fallback/events",
            json=_failure(last_harness, "external_2", "turn_2"),
        )
        assert exhausted.json()["declined"] is True
        assert exhausted.json()["attempted_models"] == ["model-a", "model-b", "model-c"]
        assert len(hc.posted_bodies) == 3
        assert original.executor.model == "model-a"
        assert original.executor.config["harness"] == primary_harness


@pytest.mark.asyncio
@pytest.mark.parametrize("proof", [False, None])
async def test_no_work_proof_is_required(proof):
    from omnigent.runner.native.fallback import NativeFallbackTurn

    spec = _spec()
    state = NativeFallbackTurn.capture(spec, spec, {"persisted_item_id": "input", "content": []})
    assert state is not None
    data = _failure("claude-native", "external", "turn")["data"]
    data["native_failure"]["before_work"] = proof
    assert state.claim(data) is None
    assert state.attempted == ["model-a"]


@pytest.mark.asyncio
async def test_failure_can_claim_before_native_injection_ack_finishes(tmp_path, monkeypatch):
    from omnigent import claude_native_bridge

    monkeypatch.setattr(claude_native_bridge, "_BRIDGE_ROOT", tmp_path / "claude")
    release = asyncio.Event()
    entered = asyncio.Event()

    class SlowFirstInjection(_ScriptedHarnessClient):
        def stream(self, method, url, *, json, timeout):
            inner = super().stream(method, url, json=json, timeout=timeout)
            first = len(self.posted_bodies) == 1

            class Context:
                async def __aenter__(self):
                    stream = await inner.__aenter__()
                    if first:
                        entered.set()
                        await release.wait()
                    return stream

                async def __aexit__(self, *args):
                    return await inner.__aexit__(*args)

            return Context()

    async def resolve(*_):
        return _spec()

    hc = SlowFirstInjection(
        [
            _sse({"type": "response.created", "response": {"id": "r1"}}),
            _sse({"type": "response.completed", "response": {"id": "r1"}}),
        ]
    )
    app = create_runner_app(
        process_manager=_FakeProcessManager(hc),
        spec_resolver=resolve,
        server_client=NullServerClient(),
    )
    async with _runner_client(app) as client:
        await client.post(
            "/v1/sessions/fast_failure/events",
            json={
                "type": "message",
                "agent_id": "role",
                "persisted_item_id": "original",
                "content": [{"type": "input_text", "text": "Review"}],
            },
        )
        await asyncio.wait_for(entered.wait(), 2)
        claim = await client.post(
            "/v1/sessions/fast_failure/events", json=_failure("claude-native", "vendor", "turn")
        )
        token = claim.json()["fallback"]["attempt_id"]
        started = await client.post(
            "/v1/sessions/fast_failure/events",
            json={"type": "native_fallback_start", "attempt_id": token},
        )
        assert started.json() == {"started": True}
        assert len(hc.posted_bodies) == 1
        release.set()
        await _settle(lambda: len(hc.posted_bodies) == 2)
        assert hc.posted_bodies[-1]["model_override"] == "model-b"


@pytest.mark.asyncio
async def test_new_input_invalidates_an_unstarted_claim(tmp_path, monkeypatch):
    from omnigent import claude_native_bridge

    monkeypatch.setattr(claude_native_bridge, "_BRIDGE_ROOT", tmp_path / "claude")

    async def resolve(*_):
        return _spec()

    hc = _ScriptedHarnessClient(
        [
            _sse({"type": "response.created", "response": {"id": "r1"}}),
            _sse({"type": "response.completed", "response": {"id": "r1"}}),
        ]
    )
    app = create_runner_app(
        process_manager=_FakeProcessManager(hc),
        spec_resolver=resolve,
        server_client=NullServerClient(),
    )
    async with _runner_client(app) as client:
        await client.post(
            "/v1/sessions/replaced/events",
            json={
                "type": "message",
                "agent_id": "role",
                "persisted_item_id": "first",
                "content": [{"type": "input_text", "text": "First"}],
            },
        )
        await _settle(lambda: len(hc.posted_bodies) == 1)
        claim = await client.post(
            "/v1/sessions/replaced/events", json=_failure("claude-native", "vendor", "turn")
        )
        token = claim.json()["fallback"]["attempt_id"]
        await client.post(
            "/v1/sessions/replaced/events",
            json={
                "type": "message",
                "agent_id": "role",
                "persisted_item_id": "second",
                "content": [{"type": "input_text", "text": "Replace the request"}],
            },
        )
        await _settle(lambda: len(hc.posted_bodies) == 2)
        rejected = await client.post(
            "/v1/sessions/replaced/events",
            json={"type": "native_fallback_start", "attempt_id": token},
        )
        assert rejected.status_code == 409
        assert len(hc.posted_bodies) == 2


@pytest.mark.asyncio
async def test_abort_fences_started_token_and_cannot_stop_newer_input(tmp_path, monkeypatch):
    from omnigent import claude_native_bridge

    monkeypatch.setattr(claude_native_bridge, "_BRIDGE_ROOT", tmp_path / "claude")

    async def resolve(*_):
        return _spec()

    hc = _ScriptedHarnessClient(
        [
            _sse({"type": "response.created", "response": {"id": "r1"}}),
            _sse({"type": "response.completed", "response": {"id": "r1"}}),
        ]
    )
    pm = _FakeProcessManager(hc)
    app = create_runner_app(
        process_manager=pm, spec_resolver=resolve, server_client=NullServerClient()
    )
    async with _runner_client(app) as client:
        await client.post(
            "/v1/sessions/aborted/events",
            json={
                "type": "message",
                "agent_id": "role",
                "persisted_item_id": "first",
                "content": [{"type": "input_text", "text": "First"}],
            },
        )
        await _settle(lambda: len(hc.posted_bodies) == 1)
        failure = _failure("claude-native", "vendor", "turn")
        token = (await client.post("/v1/sessions/aborted/events", json=failure)).json()[
            "fallback"
        ]["attempt_id"]
        start = {"type": "native_fallback_start", "attempt_id": token}
        await client.post("/v1/sessions/aborted/events", json=start)
        await _settle(lambda: len(hc.posted_bodies) == 2)
        abort = {"type": "native_fallback_abort", "attempt_id": token}
        assert (await client.post("/v1/sessions/aborted/events", json=abort)).json() == {
            "aborted": True
        }
        assert (await client.post("/v1/sessions/aborted/events", json=start)).status_code == 409
        assert (await client.post("/v1/sessions/aborted/events", json=failure)).json() == {
            "ignored": True
        }
        assert len(hc.posted_bodies) == 2
        await client.post(
            "/v1/sessions/aborted/events",
            json={
                "type": "message",
                "agent_id": "role",
                "persisted_item_id": "second",
                "content": [{"type": "input_text", "text": "New input"}],
            },
        )
        await _settle(lambda: len(hc.posted_bodies) == 3)
        prior_releases = list(pm.released)
        assert (await client.post("/v1/sessions/aborted/events", json=abort)).json() == {
            "aborted": False
        }
        assert pm.released == prior_releases


@pytest.mark.asyncio
async def test_waiting_input_survives_transition_abort_and_waits_for_cleanup(
    tmp_path, monkeypatch
):
    from omnigent import claude_native_bridge

    monkeypatch.setattr(claude_native_bridge, "_BRIDGE_ROOT", tmp_path / "claude")
    transition_entered = asyncio.Event()
    transition_cancelled = asyncio.Event()
    cleanup_entered = asyncio.Event()
    finish_cleanup = asyncio.Event()

    class BlockingReleaseManager(_FakeProcessManager):
        async def release(self, conversation_id):
            await super().release(conversation_id)
            if len(self.released) == 1:
                transition_entered.set()
                try:
                    await asyncio.Event().wait()
                finally:
                    transition_cancelled.set()
            elif len(self.released) == 2:
                cleanup_entered.set()
                await finish_cleanup.wait()

    async def resolve(*_):
        return _spec()

    hc = _ScriptedHarnessClient(
        [
            _sse({"type": "response.created", "response": {"id": "r1"}}),
            _sse({"type": "response.completed", "response": {"id": "r1"}}),
        ]
    )
    app = create_runner_app(
        process_manager=BlockingReleaseManager(hc),
        spec_resolver=resolve,
        server_client=NullServerClient(),
    )
    async with _runner_client(app) as client:
        url = "/v1/sessions/waiting_input/events"
        await client.post(
            url,
            json={
                "type": "message",
                "agent_id": "role",
                "persisted_item_id": "first",
                "content": [{"type": "input_text", "text": "First"}],
            },
        )
        await _settle(lambda: len(hc.posted_bodies) == 1)
        claim = await client.post(url, json=_failure("claude-native", "vendor", "turn"))
        token = claim.json()["fallback"]["attempt_id"]
        await client.post(url, json={"type": "native_fallback_start", "attempt_id": token})
        await asyncio.wait_for(transition_entered.wait(), 2)
        new_input = {
            "type": "message",
            "agent_id": "role",
            "persisted_item_id": "second",
            "content": [{"type": "input_text", "text": "New input"}],
        }
        # Cancelling a caller must still cancel its request, not shared recovery.
        cancelled_caller = asyncio.create_task(client.post(url, json=new_input))
        await asyncio.sleep(0.02)
        assert not cancelled_caller.done()
        cancelled_caller.cancel()
        with pytest.raises(asyncio.CancelledError):
            await cancelled_caller
        assert not transition_cancelled.is_set()

        waiting_input = asyncio.create_task(client.post(url, json=new_input))
        await asyncio.sleep(0.02)
        assert not waiting_input.done()
        abort = asyncio.create_task(
            client.post(url, json={"type": "native_fallback_abort", "attempt_id": token})
        )
        try:
            await asyncio.wait_for(cleanup_entered.wait(), 2)
            await asyncio.sleep(0.02)
            assert transition_cancelled.is_set()
            assert not waiting_input.done()
            assert len(hc.posted_bodies) == 1
        finally:
            finish_cleanup.set()
            responses = await asyncio.wait_for(
                asyncio.gather(abort, waiting_input, return_exceptions=True), 2
            )
        assert responses[0].json() == {"aborted": True}
        assert responses[1].status_code == 202
        await _settle(lambda: len(hc.posted_bodies) == 2)
        assert hc.posted_bodies[-1]["content"][-1] == {
            "type": "message",
            "role": "user",
            "content": new_input["content"],
        }
