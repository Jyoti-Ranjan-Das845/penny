"""Bounded coordinator retries distinguish confirmed starts from uncertain ones."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from starlette.responses import JSONResponse

from omnigent.runner.native.fallback import ATTEMPT_LABEL
from omnigent.server.routes.sessions.native_fallback import try_native_fallback


def _context(*, external="native-old", attempt=None):
    conv = SimpleNamespace(external_session_id=external, labels={}, terminal_launch_args=[])
    if attempt is not None:
        conv.labels[ATTEMPT_LABEL] = attempt
    store = SimpleNamespace(get_conversation=Mock(return_value=conv), apply_native_fallback=Mock())
    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace()))
    data = {
        "status": "failed",
        "response_id": "response-old",
        "output": "Provider failed",
        "native_failure": {
            "external_session_id": "native-old",
            "turn_id": "turn-old",
            "harness": "codex-native",
            "before_work": True,
            "kind": "rate_limit",
        },
    }
    return store, request, data


def _claim():
    return JSONResponse(
        {
            "fallback": {
                "attempt_id": "attempt-1",
                "model": "backup-model",
                "harness": "claude-native",
                "reasoning_effort": "max",
                "previous_model": "primary-model",
                "previous_harness": "codex-native",
                "expected_external_session_id": "native-old",
                "history_before_item_id": "original-input",
            }
        }
    )


async def _run(store, request, data, forward):
    return await try_native_fallback(
        session_id="session-1",
        data=data,
        request=request,
        conversation_store=store,
        runner_router=object(),
        forward=forward,
    )


def _events(forward):
    return [call.args[2] for call in forward.await_args_list]


@pytest.mark.asyncio
async def test_lost_first_start_ack_retries_same_token_and_commits_once():
    store, request, data = _context()
    forward = AsyncMock(side_effect=[_claim(), None, JSONResponse({"started": True})])
    assert await _run(store, request, data, forward) is True
    store.apply_native_fallback.assert_called_once()
    events = _events(forward)
    assert [event["type"] for event in events] == [
        "native_fallback_claim",
        "native_fallback_start",
        "native_fallback_start",
    ]
    assert events[1] == events[2] == {"type": "native_fallback_start", "attempt_id": "attempt-1"}
    applied = store.apply_native_fallback.call_args.kwargs
    assert applied["model"] == "backup-model"
    assert applied["reasoning_effort"] == "max"
    assert applied["history_before_item_id"] == "original-input"
    assert applied["terminal_launch_args"] == ["--permission-mode", "default"]


@pytest.mark.asyncio
async def test_two_unknown_start_acks_abort_same_token_and_expose_uncertainty():
    store, request, data = _context()
    forward = AsyncMock(side_effect=[_claim(), None, None, JSONResponse({"aborted": True})])
    assert await _run(store, request, data, forward) is False
    assert [event["type"] for event in _events(forward)] == [
        "native_fallback_claim",
        "native_fallback_start",
        "native_fallback_start",
        "native_fallback_abort",
    ]
    assert _events(forward)[-1]["attempt_id"] == "attempt-1"
    assert "final outcome could not be confirmed" in data["output"]
    store.apply_native_fallback.assert_called_once()


@pytest.mark.asyncio
async def test_unreachable_abort_still_reports_uncertainty_after_bounded_attempts():
    store, request, data = _context()
    forward = AsyncMock(side_effect=[_claim(), None, None, None])
    assert await _run(store, request, data, forward) is False
    assert forward.await_count == 4
    assert "where reachable" in data["output"]


@pytest.mark.asyncio
async def test_lost_start_ack_then_stale_token_is_visible_failure():
    store, request, data = _context()
    forward = AsyncMock(
        side_effect=[_claim(), None, JSONResponse({"started": False}, status_code=409)]
    )
    assert await _run(store, request, data, forward) is False
    assert "captured input is no longer current" in data["output"]
    assert forward.await_count == 3
    store.apply_native_fallback.assert_called_once()


@pytest.mark.asyncio
async def test_old_source_with_persisted_replacement_identity_is_ignored():
    store, request, data = _context(external="native-replacement", attempt="attempt-1")
    forward = AsyncMock()
    assert await _run(store, request, data, forward) is True
    forward.assert_not_awaited()
    store.apply_native_fallback.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize("claim_kind", ["lost", "declined", "malformed"])
async def test_cleared_native_id_without_acknowledged_claim_is_not_ignored(claim_kind):
    store, request, data = _context(external=None, attempt="attempt-1")
    response = {
        "lost": None,
        "declined": JSONResponse({"declined": True}),
        "malformed": JSONResponse(["unexpected"]),
    }[claim_kind]
    forward = AsyncMock(return_value=response)
    assert await _run(store, request, data, forward) is False
    assert forward.await_count == 1
    store.apply_native_fallback.assert_not_called()


@pytest.mark.asyncio
async def test_split_database_decline_never_starts_replacement():
    store, request, data = _context()
    store.apply_native_fallback.side_effect = NotImplementedError("single database required")
    forward = AsyncMock(return_value=_claim())
    assert await _run(store, request, data, forward) is False
    assert forward.await_count == 1


@pytest.mark.asyncio
async def test_exhausted_chain_reports_all_attempted_models_without_start():
    store, request, data = _context()
    forward = AsyncMock(
        return_value=JSONResponse(
            {"declined": True, "attempted_models": ["primary", "backup-one", "backup-two"]}
        )
    )
    assert await _run(store, request, data, forward) is False
    assert "primary, backup-one, backup-two" in data["output"]
    store.apply_native_fallback.assert_not_called()


@pytest.mark.asyncio
async def test_read_only_cross_provider_constraint_is_preserved():
    store, request, data = _context()
    store.get_conversation.return_value.terminal_launch_args = ["--sandbox", "read-only"]
    forward = AsyncMock(side_effect=[_claim(), JSONResponse({"started": True})])
    assert await _run(store, request, data, forward) is True
    assert store.apply_native_fallback.call_args.kwargs["terminal_launch_args"] == [
        "--permission-mode",
        "plan",
    ]
