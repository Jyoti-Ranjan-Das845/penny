"""Native fallback selection commits atomically without replacing the role."""

from __future__ import annotations

from dataclasses import asdict
from unittest.mock import patch
from uuid import uuid4

import pytest

from omnigent.runner.native.fallback import ATTEMPT_LABEL, HISTORY_BEFORE_LABEL
from omnigent.stores.conversation_store import FORK_SOURCE_EXTERNAL_SESSION_LABEL_KEY


def _prepare(store, agent_store=None):
    agent_id = None
    if agent_store is not None:
        agent_id = uuid4().hex
        agent_store.create(agent_id, "original-role", "synthetic-bundle")
    parent = store.create_conversation(title="parent")
    conv = store.create_conversation(
        kind="sub_agent",
        title="reader",
        agent_id=agent_id,
        sub_agent_name="reader",
        parent_conversation_id=parent.id,
        terminal_launch_args=["--permission-mode", "manual"],
    )
    store.set_external_session_id(conv.id, "native-old")
    store.set_labels(
        conv.id,
        {
            "policy.keep": "denied-tools",
            "custom": "preserve",
            FORK_SOURCE_EXTERNAL_SESSION_LABEL_KEY: "stale-source",
            "omnigent.codex_native.bypass_sandbox": "1",
        },
    )
    return store.get_conversation(conv.id)


def _apply(store, conv_id: str, **changes):
    args = {
        "attempt_id": "attempt-1",
        "expected_external_session_id": "native-old",
        "model": "backup-one",
        "harness": "claude-native",
        "reasoning_effort": "max",
        "history_before_item_id": "original-input",
        "terminal_launch_args": ["--permission-mode", "plan"],
    }
    args.update(changes)
    return store.apply_native_fallback(conv_id, **args)


def test_commit_retains_role_parent_policy_and_exact_selection(
    conversation_store, agent_store
) -> None:
    before = _prepare(conversation_store, agent_store)
    after = _apply(conversation_store, before.id)
    assert after.agent_id == before.agent_id
    assert after.parent_conversation_id == before.parent_conversation_id
    assert after.sub_agent_name == before.sub_agent_name
    assert after.kind == before.kind
    assert after.model_override == "backup-one"
    assert after.harness_override == "claude-native"
    assert after.reasoning_effort == "max"
    assert after.external_session_id is None
    assert after.terminal_launch_args == ["--permission-mode", "plan"]
    assert after.labels[ATTEMPT_LABEL] == "attempt-1"
    assert after.labels[HISTORY_BEFORE_LABEL] == "original-input"
    assert after.labels["policy.keep"] == "denied-tools"
    assert after.labels["custom"] == "preserve"
    assert after.labels["omnigent.codex_native.bypass_sandbox"] == "0"
    assert FORK_SOURCE_EXTERNAL_SESSION_LABEL_KEY not in after.labels


def test_duplicate_attempt_does_not_clear_replacement_native_session(conversation_store) -> None:
    before = _prepare(conversation_store)
    _apply(conversation_store, before.id)
    conversation_store.set_external_session_id(before.id, "native-new")
    once = conversation_store.get_conversation(before.id)
    twice = _apply(conversation_store, before.id)
    assert asdict(twice) == asdict(once)


def test_stale_source_identity_cannot_mutate_existing_selection(conversation_store) -> None:
    before = _prepare(conversation_store)
    with pytest.raises(ValueError, match="source session changed"):
        _apply(conversation_store, before.id, expected_external_session_id="wrong-source")
    assert asdict(conversation_store.get_conversation(before.id)) == asdict(before)


def test_failed_label_write_rolls_back_native_id_and_selection_then_can_retry(
    conversation_store,
) -> None:
    before = _prepare(conversation_store)
    with patch(
        "omnigent.stores.conversation_store.sqlalchemy_store._upsert_labels",
        side_effect=RuntimeError("simulated write failure"),
    ):
        with pytest.raises(RuntimeError, match="simulated write failure"):
            _apply(conversation_store, before.id)
    assert asdict(conversation_store.get_conversation(before.id)) == asdict(before)
    assert _apply(conversation_store, before.id).model_override == "backup-one"


def test_second_attempt_uses_replacement_native_id_and_preserves_original_boundary(
    conversation_store,
) -> None:
    before = _prepare(conversation_store)
    _apply(conversation_store, before.id)
    conversation_store.set_external_session_id(before.id, "native-new")
    with pytest.raises(ValueError, match="source session changed"):
        _apply(conversation_store, before.id, attempt_id="attempt-2", model="backup-two")
    after = _apply(
        conversation_store,
        before.id,
        attempt_id="attempt-2",
        model="backup-two",
        expected_external_session_id="native-new",
    )
    assert after.external_session_id is None
    assert after.model_override == "backup-two"
    assert after.labels[HISTORY_BEFORE_LABEL] == "original-input"


def test_split_database_declines_before_mutation(split_db_conversation_store) -> None:
    store = split_db_conversation_store
    before = _prepare(store)
    with pytest.raises(NotImplementedError, match="single database"):
        _apply(store, before.id)
    assert asdict(store.get_conversation(before.id)) == asdict(before)
