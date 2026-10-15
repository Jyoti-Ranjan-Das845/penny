"""Commit and start native fallback before publishing a terminal failure."""

from __future__ import annotations

import asyncio
import contextlib
import json
from typing import Any

from omnigent.runner.native.fallback import ATTEMPT_LABEL


def _payload(result: Any) -> dict[str, Any] | None:
    if result is None or not 200 <= result.status_code < 300:
        return None
    try:
        value = json.loads(result.body)
    except (TypeError, ValueError):
        return None
    return value if isinstance(value, dict) else None


def obsolete_native_status(conv: Any, data: dict[str, Any]) -> bool:
    """A switched session never accepts terminal edges from its abandoned vendor session."""
    source = data.get("native_source") or data.get("native_failure")
    return bool(
        conv.labels.get(ATTEMPT_LABEL)
        and isinstance(source, dict)
        and source.get("external_session_id")
        and source["external_session_id"] != conv.external_session_id
    )


def native_fallback_lock(request: Any, session_id: str) -> asyncio.Lock:
    """Serialize input admission with the short claim/persist/start transition."""
    locks = getattr(request.app.state, "native_fallback_locks", None)
    if locks is None:
        locks = request.app.state.native_fallback_locks = {}
    return locks.setdefault(session_id, asyncio.Lock())


async def try_native_fallback(
    *,
    session_id: str,
    data: dict[str, Any],
    request: Any,
    conversation_store: Any,
    runner_router: Any,
    forward: Any,
    admission_locked: bool = False,
) -> bool:
    """Return true only for an acknowledged replacement or an obsolete status edge."""
    if not isinstance(data.get("native_failure"), dict):
        return False
    async with (
        contextlib.nullcontext() if admission_locked else native_fallback_lock(request, session_id)
    ):
        conv = await asyncio.to_thread(conversation_store.get_conversation, session_id)
        if conv is None:
            return False
        if conv.external_session_id and obsolete_native_status(conv, data):
            return True
        claim = _payload(
            await forward(
                session_id,
                runner_router,
                {
                    "type": "native_fallback_claim",
                    "data": {**data, "expected_external_session_id": conv.external_session_id},
                },
            )
        )
        if claim is None:
            # A claim never starts work. With no acknowledgment, normal failure is safe.
            return False
        if claim.get("ignored") is True:
            return True
        decision = claim.get("fallback")
        if not isinstance(decision, dict) or not isinstance(decision.get("attempt_id"), str):
            attempted = claim.get("attempted_models")
            if isinstance(attempted, list) and len(attempted) > 1:
                data["output"] = (
                    f"{data.get('output') or 'Native turn failed'}\nAttempted models: {', '.join(str(m) for m in attempted)}."
                )
            return False
        harness = decision.get("harness")
        if harness not in {"codex-native", "claude-native"}:
            return False
        # Cross-family permissions start conservatively; vendor-specific flags
        # and stale bypass labels cannot expand the old attempt's authority.
        previous_harness = decision.get("previous_harness")
        if harness == previous_harness:
            launch_args = list(conv.terminal_launch_args or [])
        elif harness == "codex-native":
            sandbox = (
                "read-only" if "plan" in (conv.terminal_launch_args or []) else "workspace-write"
            )
            launch_args = ["--sandbox", sandbox, "--ask-for-approval", "untrusted"]
        else:
            mode = "plan" if "read-only" in (conv.terminal_launch_args or []) else "default"
            launch_args = ["--permission-mode", mode]
        try:
            await asyncio.to_thread(
                conversation_store.apply_native_fallback,
                session_id,
                attempt_id=decision["attempt_id"],
                expected_external_session_id=decision["expected_external_session_id"],
                model=decision["model"],
                harness=harness,
                reasoning_effort=decision.get("reasoning_effort"),
                history_before_item_id=decision["history_before_item_id"],
                terminal_launch_args=launch_args,
            )
        except (LookupError, ValueError, NotImplementedError):
            return False
        event = {"type": "native_fallback_start", "attempt_id": decision["attempt_id"]}
        for _ in range(2):
            result = await forward(session_id, runner_router, event)
            if result is not None and result.status_code == 409:
                data["output"] = (
                    "Native fallback could not start because its captured input is no longer current."
                )
                return False
            started = _payload(result)
            if started is not None:
                if started.get("started") is True:
                    return True
                return False
        # Fence the current token before reporting the uncertain transport
        # outcome. A later user input makes this abort a no-op on the runner.
        await forward(
            session_id,
            runner_router,
            {
                "type": "native_fallback_abort",
                "attempt_id": decision["attempt_id"],
            },
        )
        data["output"] = (
            "Native fallback acknowledgment was unavailable. Recovery was stopped where reachable; its final outcome could not be confirmed."
        )
        return False
