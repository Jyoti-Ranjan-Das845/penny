"""Bounded native fallback decisions for a single, exactly captured input."""

from __future__ import annotations

import copy
import dataclasses
import hashlib
import uuid
from typing import Any, cast

from omnigent.harness_aliases import canonicalize_harness
from omnigent.spec.types import AgentSpec

HISTORY_BEFORE_LABEL = "omnigent.native_fallback.history_before_item_id"
ATTEMPT_LABEL = "omnigent.native_fallback.attempt_id"
NATIVE_HARNESSES = frozenset({"codex-native", "claude-native"})
ELIGIBLE_FAILURES = frozenset({"model_unavailable", "rate_limit", "provider_unavailable"})


@dataclasses.dataclass(frozen=True)
class NativeCandidate:
    model: str
    harness: str
    reasoning_effort: str | None

    def as_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


def candidate_for_spec(spec: AgentSpec, message: dict[str, Any]) -> NativeCandidate:
    harness = message.get("harness_override") or spec.executor.config.get("harness")
    harness = canonicalize_harness(harness) or harness or ""
    effort = message.get("reasoning", {}).get("effort") or spec.executor.reasoning_effort
    return NativeCandidate(
        message.get("model_override") or spec.executor.model or "", harness, effort
    )


def spec_for_candidate(spec: AgentSpec, candidate: NativeCandidate) -> AgentSpec:
    """Retain role policy and tools while replacing only its native selection."""
    result = copy.deepcopy(spec)
    result.executor.model = candidate.model
    result.executor.reasoning_effort = candidate.reasoning_effort
    result.executor.config["harness"] = candidate.harness
    # CLI-specific autonomy flags cannot migrate to a different provider.
    if candidate.harness != canonicalize_harness(spec.executor.config.get("harness")):
        result.executor.config["yolo"] = False
        result.executor.config["permission_mode"] = "default"
    return result


@dataclasses.dataclass
class NativeFallbackTurn:
    message: dict[str, Any]
    spec: AgentSpec
    spec_entry: Any
    selected: NativeCandidate
    remaining: list[NativeCandidate]
    attempted: list[str]
    failures: set[tuple[str, str, str]] = dataclasses.field(default_factory=set)
    pending: dict[str, Any] | None = None
    pending_identity: tuple[str, str, str] | None = None
    closed: bool = False
    running_response_id: str | None = None
    input_response_id: str | None = None
    awaiting_replay_echo: bool = False

    @classmethod
    def capture(
        cls, spec: AgentSpec, spec_entry: Any, message: dict[str, Any]
    ) -> NativeFallbackTurn | None:
        primary = candidate_for_spec(spec, message)
        fallbacks = getattr(spec.executor, "fallbacks", None)
        item_id = message.get("persisted_item_id") or message.get("pending_input_id")
        if (
            primary.harness not in NATIVE_HARNESSES
            or not fallbacks
            or not isinstance(item_id, str)
            or not item_id
        ):
            return None
        remaining = [
            NativeCandidate(
                f.model, canonicalize_harness(f.harness) or f.harness, f.reasoning_effort
            )
            for f in fallbacks
        ]
        # A successful fallback remains selected for the next user input.
        for index, candidate in enumerate(remaining):
            if (candidate.harness, candidate.model) == (primary.harness, primary.model):
                remaining = remaining[index + 1 :]
                break
        remaining = [
            c for c in remaining if (c.harness, c.model) != (primary.harness, primary.model)
        ][:2]
        return cls(
            copy.deepcopy(message),
            copy.deepcopy(spec),
            spec_entry,
            primary,
            remaining,
            [primary.model],
        )

    def claim(self, data: dict[str, Any]) -> dict[str, Any] | None:
        failure = data.get("native_failure")
        if not isinstance(failure, dict):
            return None
        identity = (
            failure.get("harness"),
            failure.get("external_session_id"),
            failure.get("turn_id"),
        )
        if not all(isinstance(v, str) and v for v in identity):
            return None
        identity = cast(tuple[str, str, str], identity)
        if identity in self.failures:
            return self.pending if identity == self.pending_identity else {"ignored": True}
        if (
            self.closed
            or failure.get("before_work") is not True
            or failure.get("kind") not in ELIGIBLE_FAILURES
        ):
            return None
        if identity[0] != self.selected.harness:
            return None
        reported = failure.get("model")
        if reported and reported != self.selected.model:
            return None
        expected = data.get("expected_external_session_id")
        if not expected or identity[1] != expected:
            return None
        if (
            self.running_response_id
            and data.get("response_id")
            and data["response_id"] != self.running_response_id
        ):
            return None
        if self.input_response_id:
            expected_response = (
                ("codex_" + identity[2])
                if identity[0] == "codex-native"
                else ("resp_claude_" + hashlib.sha256(identity[2].encode()).hexdigest()[:32])
            )
            if expected_response != self.input_response_id:
                return None
        if not self.message.get("persisted_item_id"):
            return None
        if not self.remaining:
            self.closed = True
            return None
        candidate = self.remaining.pop(0)
        self.failures.add(identity)
        self.pending_identity = identity
        self.pending = {
            "attempt_id": uuid.uuid4().hex,
            "history_before_item_id": self.message["persisted_item_id"],
            "previous_model": self.selected.model,
            "previous_harness": self.selected.harness,
            "expected_external_session_id": identity[1],
            **candidate.as_dict(),
        }
        self.selected = candidate
        self.attempted.append(candidate.model)
        self.running_response_id = None
        self.input_response_id = None
        return self.pending
