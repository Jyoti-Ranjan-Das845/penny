"""A captured input has one bounded, identity-checked native fallback chain."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict

import pytest

from omnigent.runner.native.fallback import NativeCandidate, NativeFallbackTurn, spec_for_candidate
from omnigent.spec import AgentSpec, ExecutorFallback, ExecutorSpec


def _spec() -> AgentSpec:
    spec = AgentSpec(
        spec_version=1,
        name="writer",
        instructions="Preserve source meaning.",
        executor=ExecutorSpec(
            model="primary",
            reasoning_effort="xhigh",
            config={"harness": "codex-native", "yolo": False},
            fallbacks=[
                ExecutorFallback("backup-one", "claude-native", "max"),
                ExecutorFallback("backup-two", "claude-native", "max"),
            ],
        ),
    )
    spec.sub_agents = [
        AgentSpec(spec_version=1, name="reader", instructions="Read independently.")
    ]
    spec.tools.agents = ["reader"]
    return spec


def _turn(**message) -> NativeFallbackTurn:
    captured = NativeFallbackTurn.capture(
        _spec(),
        object(),
        {
            "persisted_item_id": "item-1",
            "content": [{"type": "input_text", "text": "original"}],
            **message,
        },
    )
    assert captured is not None
    return captured


def _failure(
    turn: NativeFallbackTurn, external: str = "native-1", native_turn: str = "turn-1"
) -> dict:
    return {
        "expected_external_session_id": external,
        "response_id": "response-1",
        "native_failure": {
            "before_work": True,
            "kind": "rate_limit",
            "harness": turn.selected.harness,
            "model": turn.selected.model,
            "external_session_id": external,
            "turn_id": native_turn,
        },
    }


def test_two_failures_use_ordered_backups_then_exhaust_without_cycle() -> None:
    turn = _turn()
    first = turn.claim(_failure(turn))
    assert first["model"] == "backup-one"
    assert first["reasoning_effort"] == "max"
    assert first["history_before_item_id"] == "item-1"
    second = turn.claim(_failure(turn, "native-2", "turn-2"))
    assert second["model"] == "backup-two"
    assert second["attempt_id"] != first["attempt_id"]
    assert turn.claim(_failure(turn, "native-3", "turn-3")) is None
    assert turn.closed
    assert turn.attempted == ["primary", "backup-one", "backup-two"]


def test_duplicate_claim_does_not_consume_another_candidate() -> None:
    turn = _turn()
    failure = _failure(turn)
    first = turn.claim(failure)
    assert turn.claim(failure) == first
    assert turn.attempted == ["primary", "backup-one"]
    turn.claim(_failure(turn, "native-2", "turn-2"))
    assert turn.claim(failure) == {"ignored": True}
    assert turn.attempted == ["primary", "backup-one", "backup-two"]


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("before_work", False),
        ("before_work", "true"),
        ("before_work", None),
        ("kind", "authentication_failed"),
        ("kind", "permission_denied"),
        ("kind", "cancelled"),
        ("kind", "unknown"),
        ("harness", "claude-native"),
        ("model", "other-model"),
        ("external_session_id", "other-session"),
        ("turn_id", None),
    ],
)
def test_unsafe_or_unrelated_failure_leaves_chain_untouched(key: str, value: object) -> None:
    turn = _turn()
    failure = _failure(turn)
    failure["native_failure"][key] = value
    assert turn.claim(failure) is None
    assert turn.selected.model == "primary"
    assert len(turn.remaining) == 2
    assert not turn.failures


def test_active_response_and_closed_turn_are_checked() -> None:
    turn = _turn()
    turn.running_response_id = "another-response"
    assert turn.claim(_failure(turn)) is None
    turn.running_response_id = None
    turn.closed = True
    assert turn.claim(_failure(turn)) is None


def test_pending_input_must_resolve_to_persisted_item_before_claim() -> None:
    turn = NativeFallbackTurn.capture(_spec(), object(), {"pending_input_id": "pending-1"})
    assert turn is not None
    assert turn.claim(_failure(turn)) is None
    turn.message["persisted_item_id"] = "resolved-item"
    assert turn.claim(_failure(turn))["history_before_item_id"] == "resolved-item"
    assert NativeFallbackTurn.capture(_spec(), object(), {}) is None


def test_no_chain_or_non_native_executor_has_no_capture() -> None:
    spec = _spec()
    spec.executor.fallbacks = []
    assert NativeFallbackTurn.capture(spec, None, {"persisted_item_id": "item"}) is None
    spec = _spec()
    spec.executor.config["harness"] = "claude-sdk"
    assert NativeFallbackTurn.capture(spec, None, {"persisted_item_id": "item"}) is None


def test_capture_freezes_original_input_and_current_backup_does_not_cycle() -> None:
    message = {"persisted_item_id": "item", "content": ["original"]}
    spec = _spec()
    turn = NativeFallbackTurn.capture(spec, None, message)
    message["content"].append("later")
    spec.instructions = "later"
    assert turn.message["content"] == ["original"]
    assert turn.spec.instructions == "Preserve source meaning."
    selected_backup = _turn(
        model_override="backup-one", harness_override="claude-native", reasoning={"effort": "high"}
    )
    assert [candidate.model for candidate in selected_backup.remaining] == ["backup-two"]


def test_candidate_preserves_role_instructions_tools_children_and_source() -> None:
    spec = _spec()
    before = deepcopy(spec)
    changed = spec_for_candidate(spec, NativeCandidate("backup-one", "claude-native", "max"))
    changed_fields, original_fields = asdict(changed), asdict(spec)
    changed_fields.pop("executor")
    original_fields.pop("executor")
    assert changed_fields == original_fields
    assert spec == before
    assert changed.executor.model == "backup-one"
    assert changed.executor.reasoning_effort == "max"
    assert changed.executor.config["harness"] == "claude-native"
    assert changed.executor.config["yolo"] is False
    assert changed.executor.config["permission_mode"] not in ("bypassPermissions", "acceptEdits")
    changed.sub_agents[0].instructions = "modified copy"
    assert spec.sub_agents[0].instructions == "Read independently."
