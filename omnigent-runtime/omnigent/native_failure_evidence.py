"""Conservative availability evidence for replaying a native turn before work."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


def codex_availability_kind(error: dict[str, object]) -> str | None:
    """Classify protocol errors without treating arbitrary failures as outages."""
    info = error.get("codexErrorInfo")
    variant = info if isinstance(info, str) else ""
    status: object = None
    if isinstance(info, dict):
        variant = info.get("type") or info.get("kind") or info.get("variant") or ""
        status = info.get("httpStatusCode")
        if len(info) == 1 and not variant:
            variant, detail = next(iter(info.items()))
            if isinstance(detail, dict):
                status = detail.get("httpStatusCode")
    if status in (401, 403):
        return None
    if variant in ("usageLimitExceeded", "rateLimitExceeded") or status == 429:
        return "rate_limit"
    if variant in ("modelNotFound", "modelUnavailable"):
        return "model_unavailable"
    if variant in ("serverOverloaded", "serverUnavailable", "internalServerError") or status in (
        500,
        502,
        503,
        504,
    ):
        return "provider_unavailable"
    return None


def claude_failure_evidence(
    *,
    error: str | None,
    transcript_path: Path | None,
    external_session_id: str | None,
    response_id: str | None,
    last_assistant_message: str | None,
    model: str | None = None,
) -> dict[str, object] | None:
    """Require the current user UUID and a complete transcript with no work."""
    kind = {
        "rate_limit": "rate_limit",
        "overloaded": "provider_unavailable",
        "model_not_found": "model_unavailable",
        "server_error": "provider_unavailable",
    }.get(error or "")
    if kind is None or transcript_path is None or not external_session_id or not response_id:
        return None
    try:
        # Bound memory use; a partial or oversized transcript cannot prove no work.
        with transcript_path.open("rb") as stream:
            raw = stream.read(16 * 1024 * 1024 + 1)
        if len(raw) > 16 * 1024 * 1024 or not raw.endswith(b"\n"):
            return None
        rows = [json.loads(line) for line in raw.splitlines() if line.strip()]
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    if not rows or any(not isinstance(row, dict) for row in rows):
        return None

    # A normal user record resets the real forwarder's current_response_id.
    # The first assistant record then establishes it from ITS UUID/requestId,
    # rather than the user's UUID. Inspect the same user parsing semantics to
    # reject command scaffolding, tool results, and compaction continuations.
    from omnigent.claude_native_bridge import _user_transcript_items_from_entry

    starts = []
    for index, row in enumerate(rows):
        if row.get("type") != "user" or row.get("isMeta") or row.get("isCompactSummary"):
            continue
        message = row.get("message")
        if not isinstance(message, dict) or message.get("role") != "user":
            return None
        content = message.get("content")
        if not isinstance(content, (str, list)):
            return None
        if isinstance(content, list):
            if any(not isinstance(block, dict) for block in content):
                return None
            if any(block.get("type") == "tool_result" for block in content):
                continue
            if any(block.get("type") not in ("text", "image", "document") for block in content):
                return None
        next_response, items = _user_transcript_items_from_entry(
            row,
            line_number=index + 1,
            record_offset=None,
            agent_name="native-failure-evidence",
            current_response_id=None,
        )
        if next_response is None and any(
            item.item_type == "message"
            and item.data.get("role") == "user"
            and not item.data.get("is_meta")
            for item in items
        ):
            starts.append(index)
    if not starts:
        return None
    current = rows[starts[-1]]
    user_id = current.get("uuid")
    if (
        not isinstance(user_id, str)
        or not user_id
        or current.get("sessionId") != external_session_id
        or sum(row.get("uuid") == user_id for row in rows) != 1
    ):
        return None

    error_texts: list[str] = []
    first_error_source: str | None = None
    ancestors = {user_id}
    for row in rows[starts[-1] + 1 :]:
        # Only explicit API-error messages and bookkeeping have no model work.
        if row.get("type") == "assistant" and row.get("isApiErrorMessage") is True:
            message = row.get("message")
            content = message.get("content") if isinstance(message, dict) else None
            if (
                not isinstance(message, dict)
                or message.get("role") != "assistant"
                or row.get("sessionId") != external_session_id
                or row.get("parentUuid") not in ancestors
                or not isinstance(content, list)
                or not content
                or any(
                    not isinstance(block, dict)
                    or block.get("type") != "text"
                    or not isinstance(block.get("text"), str)
                    or not block["text"]
                    for block in content
                )
            ):
                return None
            source = row.get("uuid") or row.get("requestId")
            if not isinstance(source, str) or not source or source in ancestors:
                return None
            if first_error_source is None:
                first_error_source = source
            ancestors.add(source)
            error_texts.append("\n".join(block["text"] for block in content))
            continue
        if row.get("type") in ("file-history-snapshot", "queue-operation"):
            continue
        return None

    def response_for(source: str) -> str:
        return "resp_claude_" + hashlib.sha256(source.encode()).hexdigest()[:32]

    # A no-assistant failure may carry a positively identified user turn. With
    # assistant API errors, use the exact first-assistant ID the forwarder uses.
    expected_response = response_for(first_error_source or user_id)
    if response_id != expected_response:
        return None
    if last_assistant_message and (not error_texts or last_assistant_message != error_texts[-1]):
        return None
    result: dict[str, object] = {
        "harness": "claude-native",
        "turn_id": current["uuid"],
        "external_session_id": external_session_id,
        "kind": kind,
        "before_work": True,
    }
    if model:
        result["model"] = model
    return result
