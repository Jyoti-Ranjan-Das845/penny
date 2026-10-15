"""Replay evidence is emitted only for identifiable pre-work provider failures."""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest

from omnigent import codex_native_forwarder as fwd
from omnigent.codex_native_bridge import CodexNativeBridgeState, write_bridge_state
from omnigent.native_failure_evidence import codex_availability_kind


@pytest.mark.parametrize(
    ("info", "expected"),
    [
        ("usageLimitExceeded", "rate_limit"),
        ("rateLimitExceeded", "rate_limit"),
        ("modelNotFound", "model_unavailable"),
        ("serverOverloaded", "provider_unavailable"),
        ("internalServerError", "provider_unavailable"),
        ({"responseTooManyFailedAttempts": {"httpStatusCode": 503}}, "provider_unavailable"),
        ("unauthorized", None),
        ("badRequest", None),
        ({"httpStatusCode": 503}, "provider_unavailable"),
        ({"httpConnectionFailed": {"httpStatusCode": 429}}, "rate_limit"),
        ({"httpStatusCode": 401}, None),
        ({"httpStatusCode": 403}, None),
        ("contextWindowExceeded", None),
        ("policyDenied", None),
        ("unknown", None),
    ],
)
def test_only_known_availability_errors(info: object, expected: str | None) -> None:
    assert codex_availability_kind({"codexErrorInfo": info}) == expected


def _params(*, items: list[dict[str, object]] | None = None) -> dict[str, object]:
    turn: dict[str, object] = {
        "id": "turn-one",
        "status": "failed",
        "error": {"message": "Quota exhausted", "codexErrorInfo": "usageLimitExceeded"},
    }
    if items is not None:
        turn["items"] = items
    return {"threadId": "thread-one", "turn": turn}


def test_missing_activity_history_does_not_imply_safe_replay() -> None:
    params = _params()
    error = fwd._terminal_error_from_turn(params)
    assert fwd._codex_failure_evidence(params, error, fwd._CodexForwarderState()) is None
    assert fwd._codex_failure_evidence(params, error, None) is None


@pytest.mark.parametrize(
    "item_type", ["agentMessage", "commandExecution", "reasoning", "mcpToolCall"]
)
def test_complete_turn_with_any_work_is_not_replayed(item_type: str) -> None:
    params = _params(items=[{"type": "userMessage"}, {"type": item_type}])
    assert fwd._codex_failure_evidence(params, fwd._terminal_error_from_turn(params), None) is None


def test_completed_empty_turn_proves_no_work_after_reconnect() -> None:
    params = _params(items=[])
    evidence = fwd._codex_failure_evidence(params, fwd._terminal_error_from_turn(params), None)
    assert evidence is not None
    assert evidence["turn_id"] == "turn-one"
    assert evidence["external_session_id"] == "thread-one"


@pytest.mark.parametrize(
    "method, payload",
    [
        ("item/agentMessage/delta", {"delta": "partial output"}),
        ("item/started", {"item": {"type": "commandExecution"}}),
        ("item/reasoning/textDelta", {"delta": "reasoning"}),
        ("turn/plan/updated", {"plan": []}),
    ],
)
def test_observed_work_overrides_incomplete_terminal_item_list(method: str, payload: dict) -> None:
    state = fwd._CodexForwarderState()
    fwd._note_fallback_activity("turn/started", _params(), state)
    fwd._note_fallback_activity(method, {"turnId": "turn-one", **payload}, state)
    # A duplicate start must not erase evidence of work.
    fwd._note_fallback_activity("turn/started", _params(), state)
    params = _params(items=[])
    assert (
        fwd._codex_failure_evidence(params, fwd._terminal_error_from_turn(params), state) is None
    )


@pytest.mark.parametrize("terminal_method", ["error", "turn/completed", "turn/failed"])
async def test_real_forwarder_posts_safe_failure_metadata(
    tmp_path: Path, terminal_method: str
) -> None:
    write_bridge_state(
        tmp_path,
        CodexNativeBridgeState(
            session_id="conversation",
            socket_path=str(tmp_path / "app.sock"),
            thread_id="thread-one",
            codex_home=str(tmp_path / "codex-home"),
        ),
    )
    posts = []

    def transport(request: httpx.Request) -> httpx.Response:
        if request.method == "POST":
            posts.append(json.loads(request.content))
        return httpx.Response(200, json={})

    async with httpx.AsyncClient(
        base_url="http://test", transport=httpx.MockTransport(transport)
    ) as client:
        state = fwd._CodexForwarderState(model="configured-test-model")
        usage = fwd._SessionUsageCoalescer(client, "conversation")
        tracker = fwd._CodexElicitationTaskTracker()

        async def send(method: str, params: dict) -> None:
            await fwd._handle_event(
                client,
                session_id="conversation",
                bridge_dir=tmp_path,
                event={"method": method, "params": params},
                usage_coalescer=usage,
                elicitation_tracker=tracker,
                expected_thread_id="thread-one",
                forwarder_state=state,
            )

        await send("turn/started", {"threadId": "thread-one", "turn": {"id": "turn-one"}})
        if terminal_method == "error":
            params = {
                "threadId": "thread-one",
                "turnId": "turn-one",
                "willRetry": False,
                "error": {"message": "Quota exhausted", "codexErrorInfo": "usageLimitExceeded"},
            }
            await send("error", {**params, "willRetry": True})
            assert not any(p.get("data", {}).get("status") == "failed" for p in posts)
        else:
            params = _params(items=[])
        await send(terminal_method, params)
        failures = [p["data"] for p in posts if p.get("data", {}).get("status") == "failed"]
        assert len(failures) == 1
        assert failures[0]["native_failure"] == {
            "harness": "codex-native",
            "turn_id": "turn-one",
            "external_session_id": "thread-one",
            "kind": "rate_limit",
            "before_work": True,
            "model": "configured-test-model",
        }
