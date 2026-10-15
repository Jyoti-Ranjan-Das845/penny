"""Native provider failures traverse the real server and runner event routes."""

from __future__ import annotations

import asyncio
import json

import httpx
import pytest

from omnigent.runner import create_runner_app
from omnigent.runtime import pending_inputs
from omnigent.stores.conversation_store.sqlalchemy_store import SqlAlchemyConversationStore
from tests.runner.conftest import _FakeProcessManager, _runner_client, _ScriptedHarnessClient, _sse
from tests.runner.helpers import NullServerClient
from tests.runner.test_native_fallback_runtime import _settle, _spec
from tests.server.helpers import create_test_agent


@pytest.mark.asyncio
@pytest.mark.parametrize("start_accepted", [True, False], ids=["start-ack", "failure-delivery"])
async def test_new_message_waits_until_fallback_transition_is_delivered(
    client, db_uri, monkeypatch, start_accepted
):
    """Input admission cannot supersede a claimed, persisted fallback mid-transition."""
    from omnigent.server.routes import sessions

    agent = await create_test_agent(client)
    session_id = agent["_session_id"]
    store = SqlAlchemyConversationStore(db_uri)
    store.set_external_session_id(session_id, "native-old")
    original = await client.post(
        f"/v1/sessions/{session_id}/events",
        json={
            "type": "external_conversation_item",
            "data": {
                "item_type": "message",
                "item_data": {
                    "role": "user",
                    "content": [{"type": "input_text", "text": "Original request"}],
                },
            },
        },
    )
    assert original.status_code == 202, original.text
    original_item_id = original.json()["item_id"]
    transition_paused = asyncio.Event()
    release_transition = asyncio.Event()
    message_attempted = asyncio.Event()
    order = []
    forwarded_messages = []

    async def handle_runner(request):
        body = json.loads(request.content)
        if request.url.path.endswith("/resources/terminals"):
            return httpx.Response(200, json={"terminal_id": "replacement-terminal"})
        event_type = body["type"]
        order.append(event_type)
        if event_type == "native_fallback_claim":
            return httpx.Response(
                200,
                json={
                    "fallback": {
                        "attempt_id": "attempt-1",
                        "model": "backup-model",
                        "harness": "claude-native",
                        "reasoning_effort": "max",
                        "previous_harness": "codex-native",
                        "expected_external_session_id": "native-old",
                        "history_before_item_id": original_item_id,
                    }
                },
            )
        if event_type == "native_fallback_start":
            if not start_accepted:
                return httpx.Response(409, json={"started": False})
            transition_paused.set()
            await release_transition.wait()
            order.append("start_acknowledged")
            return httpx.Response(200, json={"started": True})
        if event_type == "external_session_status":
            assert not start_accepted
            assert body["data"]["status"] == "failed"
            assert "captured input is no longer current" in body["data"]["output"]
            transition_paused.set()
            await release_transition.wait()
            order.append("failure_delivered")
            return httpx.Response(200, json={"queued": False})
        assert event_type == "message", body
        forwarded_messages.append(body)
        return httpx.Response(202, json={"queued": True})

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handle_runner), base_url="http://runner"
    ) as runner_client:

        async def runner_for(*_):
            return runner_client

        monkeypatch.setattr(sessions, "_get_runner_client", runner_for)
        failure_task = asyncio.create_task(
            client.post(
                f"/v1/sessions/{session_id}/events",
                json={
                    "type": "external_session_status",
                    "data": {
                        "status": "failed",
                        "output": "Primary model unavailable",
                        "native_failure": {
                            "harness": "codex-native",
                            "external_session_id": "native-old",
                            "turn_id": "old-turn",
                            "kind": "model_unavailable",
                            "before_work": True,
                        },
                    },
                },
            )
        )
        message_task = None
        try:
            await asyncio.wait_for(transition_paused.wait(), timeout=5)
            # The switch is persisted; either the start ACK or failure delivery is pending.
            assert store.get_conversation(session_id).model_override == "backup-model"

            async def send_new_message():
                message_attempted.set()
                return await client.post(
                    f"/v1/sessions/{session_id}/events",
                    json={
                        "type": "message",
                        "data": {
                            "role": "user",
                            "content": [{"type": "input_text", "text": "New request"}],
                        },
                    },
                )

            message_task = asyncio.create_task(send_new_message())
            await message_attempted.wait()
            with pytest.raises(TimeoutError):
                await asyncio.wait_for(asyncio.shield(message_task), timeout=0.1)
            assert forwarded_messages == []
            before_delivery = ["native_fallback_claim", "native_fallback_start"]
            if not start_accepted:
                before_delivery.append("external_session_status")
            assert order == before_delivery

            release_transition.set()
            failure, message = await asyncio.wait_for(
                asyncio.gather(failure_task, message_task), timeout=5
            )
            assert failure.status_code == 202, failure.text
            expected_failure = {"queued": False}
            if start_accepted:
                expected_failure["native_fallback"] = True
            assert failure.json() == expected_failure
            assert message.status_code == 202, message.text
            assert message.json()["queued"] is True
            assert isinstance(message.json()["pending_id"], str)
            assert order == [
                *before_delivery,
                "start_acknowledged" if start_accepted else "failure_delivered",
                "message",
            ]
            assert forwarded_messages[0]["content"] == [
                {"type": "input_text", "text": "New request"}
            ]
        finally:
            release_transition.set()
            tasks = [failure_task] + ([message_task] if message_task is not None else [])
            for task in tasks:
                if not task.done():
                    task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)


@pytest.mark.asyncio
@pytest.mark.parametrize("failures", [1, 3])
async def test_provider_failure_chain_has_one_terminal_delivery(
    client, db_uri, monkeypatch, tmp_path, failures
):
    import omnigent.runner.app as runner_module
    from omnigent import claude_native_bridge, codex_native_bridge
    from omnigent.server.routes import sessions

    monkeypatch.setattr(claude_native_bridge, "_BRIDGE_ROOT", tmp_path / "claude")
    monkeypatch.setattr(codex_native_bridge, "_BRIDGE_ROOT", tmp_path / "codex")
    agent = await create_test_agent(client)
    session_id = agent["_session_id"]
    store = SqlAlchemyConversationStore(db_uri)
    store.set_external_session_id(session_id, "vendor_0")
    store.set_labels(session_id, {"policy.keep": "required"})
    original_spec = _spec()

    async def resolve(*_):
        return original_spec

    hc = _ScriptedHarnessClient(
        [
            _sse({"type": "response.created", "response": {"id": "injection"}}),
            _sse({"type": "response.completed", "response": {"id": "injection"}}),
        ]
    )
    pm = _FakeProcessManager(hc)
    runner = create_runner_app(
        process_manager=pm, spec_resolver=resolve, server_client=NullServerClient()
    )
    terminal = []
    actual_terminal = runner_module.mark_subagent_work_terminal

    def record_terminal(sid, *, status, output):
        terminal.append((sid, status, output))
        return actual_terminal(sid, status=status, output=output)

    monkeypatch.setattr(runner_module, "mark_subagent_work_terminal", record_terminal)
    published = []
    monkeypatch.setattr(
        sessions.session_stream, "publish", lambda sid, event: published.append((sid, event))
    )
    async with _runner_client(runner) as runner_client:

        async def runner_for(*_):
            return runner_client

        monkeypatch.setattr(sessions, "_get_runner_client", runner_for)
        content = [{"type": "input_text", "text": "Review the supplied evidence."}]
        pending_id = pending_inputs.record(session_id, content)
        await runner_client.post(
            f"/v1/sessions/{session_id}/events",
            json={
                "type": "message",
                "agent_id": agent["id"],
                "pending_input_id": pending_id,
                "content": content,
            },
        )
        await _settle(lambda: len(hc.posted_bodies) == 1)
        committed = await client.post(
            f"/v1/sessions/{session_id}/events",
            json={
                "type": "external_conversation_item",
                "data": {
                    "item_type": "message",
                    "item_data": {"role": "user", "content": content},
                },
            },
        )
        assert committed.status_code == 202, committed.text
        item_id = committed.json()["item_id"]
        for index in range(failures):
            harness = "codex-native" if index == 2 else "claude-native"
            payload = {
                "type": "external_session_status",
                "data": {
                    "status": "failed",
                    "output": "Selected model is unavailable.",
                    "native_failure": {
                        "harness": harness,
                        "external_session_id": f"vendor_{index}",
                        "turn_id": f"turn_{index}",
                        "kind": "model_unavailable",
                        "before_work": True,
                    },
                },
            }
            # Duplicate provider terminal notifications must claim one attempt.
            results = (
                await asyncio.gather(
                    client.post(f"/v1/sessions/{session_id}/events", json=payload),
                    client.post(f"/v1/sessions/{session_id}/events", json=payload),
                )
                if index < 2
                else [await client.post(f"/v1/sessions/{session_id}/events", json=payload)]
            )
            assert all(r.status_code == 202 for r in results), [r.text for r in results]
            if index < 2:
                assert all(r.json().get("native_fallback") is True for r in results)
                await _settle(lambda expected=index + 2: len(hc.posted_bodies) == expected)
                assert terminal == []
                changed = store.get_conversation(session_id)
                assert changed.agent_id == agent["id"]
                assert changed.labels["policy.keep"] == "required"
                assert changed.labels["omnigent.native_fallback.history_before_item_id"] == item_id
                assert changed.model_override == ["model-b", "model-c"][index]
                store.set_external_session_id(session_id, f"vendor_{index + 1}")
                # An abandoned source cannot terminate the replacement, even
                # when its late error lacks replay eligibility evidence.
                old = await client.post(
                    f"/v1/sessions/{session_id}/events",
                    json={
                        "type": "external_session_status",
                        "data": {
                            "status": "failed",
                            "output": "Late old error",
                            "native_source": {
                                "harness": harness,
                                "external_session_id": f"vendor_{index}",
                            },
                        },
                    },
                )
                assert old.json().get("ignored") is True
                assert terminal == []
        if failures == 1:
            done = await client.post(
                f"/v1/sessions/{session_id}/events",
                json={
                    "type": "external_session_status",
                    "data": {
                        "status": "idle",
                        "output": "Reviewed with citations.",
                        "native_source": {
                            "harness": "claude-native",
                            "external_session_id": "vendor_1",
                        },
                    },
                },
            )
            assert done.status_code == 202
            assert [row[1] for row in terminal] == ["completed"]
        else:
            assert [row[1] for row in terminal] == ["failed"]
            assert "model-a, model-b, model-c" in terminal[0][2]
        failed = [
            event
            for _, event in published
            if event.get("type") == "session.status" and event.get("status") == "failed"
        ]
        assert len(failed) == (1 if failures == 3 else 0)
