"""Native fallback declarations survive both spec formats and reject unsafe chains."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest
import yaml

from omnigent.errors import OmnigentError
from omnigent.inner.loader import _parse_executor_spec
from omnigent.spec import AgentSpec, ExecutorFallback, ExecutorSpec, parse, validate
from omnigent.spec.omnigent import agent_def_to_agent_spec, agent_spec_to_agent_def


def _spec() -> AgentSpec:
    return AgentSpec(
        spec_version=1,
        name="fallback-test",
        instructions="Keep the original instructions.",
        executor=ExecutorSpec(
            model="primary-test-model",
            reasoning_effort="high",
            config={"harness": "codex-native", "yolo": False},
            fallbacks=[
                ExecutorFallback("second-test-model", "claude-native", "max"),
                ExecutorFallback("third-test-model", "codex-native", "high"),
            ],
        ),
    )


def test_bundle_load_retains_order_and_reasoning(tmp_path: Path) -> None:
    (tmp_path / "config.yaml").write_text(
        yaml.safe_dump(
            {
                "spec_version": 1,
                "name": "fallback-test",
                "executor": {
                    "model": "primary-test-model",
                    "config": {"harness": "codex-native", "yolo": False},
                    "fallbacks": [
                        {
                            "model": "second-test-model",
                            "harness": "claude-native",
                            "reasoning_effort": "max",
                        },
                        {
                            "model": "third-test-model",
                            "harness": "codex-native",
                            "reasoning_effort": "high",
                        },
                    ],
                },
            }
        )
    )
    parsed = parse(tmp_path)
    assert parsed.executor.fallbacks == _spec().executor.fallbacks
    assert validate(parsed).valid
    assert str(parsed.executor.config["yolo"]).lower() == "false"


@pytest.mark.parametrize(
    "raw",
    [
        "model",
        {},
        ["model"],
        [None],
        [{"model": "", "harness": "codex-native"}],
        [{"model": 123, "harness": "codex-native"}],
        [{"model": "bad model", "harness": "codex-native"}],
        [{"model": "backup", "harness": "unknown"}],
        [{"model": "backup", "harness": "codex-native", "reasoning_effort": 4}],
        [{"model": "backup", "harness": "codex-native", "yolo": True}],
        [{"model": "backup", "harness": "codex-native"}] * 3,
    ],
)
def test_malformed_candidates_are_rejected_in_both_formats(tmp_path: Path, raw: object) -> None:
    (tmp_path / "config.yaml").write_text(
        yaml.safe_dump(
            {
                "spec_version": 1,
                "name": "test",
                "executor": {"fallbacks": raw},
            }
        )
    )
    with pytest.raises(OmnigentError, match=r"executor\.fallbacks"):
        parse(tmp_path)
    with pytest.raises(OmnigentError, match=r"executor\.fallbacks"):
        _parse_executor_spec({"model": "primary", "harness": "codex-native", "fallbacks": raw})


@pytest.mark.parametrize(
    ("field", "value", "expected"),
    [
        ("model", None, "explicit primary"),
        ("type", "agents_sdk", "native primary"),
        ("config", {"harness": "claude-sdk"}, "native primary"),
        ("connection", {"base_url": "https://example.test"}, "host-managed"),
        ("profile", "credential-profile", "host-managed"),
        ("config", {"harness": "codex-native", "profile": "credential-profile"}, "host-managed"),
        ("fallbacks", [ExecutorFallback("primary-test-model", "codex-native")], "duplicates"),
        ("fallbacks", [ExecutorFallback("backup", "claude-native")] * 2, "duplicates"),
        ("fallbacks", [ExecutorFallback("backup", "claude-native")] * 3, "at most two"),
        (
            "fallbacks",
            [ExecutorFallback("backup", "codex-native", "unsupported")],
            "reasoning_effort",
        ),
        ("fallbacks", [ExecutorFallback("backup", "unsupported")], "harness"),
    ],
)
def test_invalid_chains_fail_validation(field: str, value: object, expected: str) -> None:
    spec = _spec()
    spec.executor = replace(spec.executor, **{field: value})
    errors = validate(spec).errors
    assert any(
        e.path.startswith("executor.fallbacks") and expected in (e.path + e.message)
        for e in errors
    )


def test_default_empty_chain_preserves_old_specs() -> None:
    spec = _spec()
    spec.executor = replace(spec.executor, fallbacks=[])
    assert validate(spec).valid
    assert _parse_executor_spec("primary-test-model").fallbacks == []


def test_primary_and_child_chains_survive_translation() -> None:
    spec = _spec()
    child = replace(_spec(), name="reader")
    spec.sub_agents = [child]
    spec.tools.agents = ["reader"]
    translated = agent_spec_to_agent_def(spec)
    restored = agent_def_to_agent_spec(translated)
    assert restored.executor.fallbacks == spec.executor.fallbacks
    assert restored.sub_agents[0].executor.fallbacks == child.executor.fallbacks
    assert restored.instructions == spec.instructions


def test_standalone_executor_chain_survives_translation() -> None:
    inner = _parse_executor_spec(
        {
            "model": "primary-test-model",
            "harness": "codex-native",
            "fallbacks": [
                {"model": "backup", "harness": "claude-native", "reasoning_effort": "max"}
            ],
        }
    )
    assert inner is not None
    from omnigent.inner.datamodel import AgentDef

    spec = agent_def_to_agent_spec(AgentDef(name="test", prompt="original", executor=inner))
    assert spec.executor.fallbacks == inner.fallbacks
