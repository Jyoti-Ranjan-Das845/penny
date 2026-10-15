"""Use actual transcript response identities for safe Claude recovery evidence."""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from pathlib import Path

import httpx
import pytest

from omnigent import claude_native_forwarder as forwarder
from omnigent.claude_native_bridge import read_transcript_items_since, record_hook_event
from omnigent.native_failure_evidence import claude_failure_evidence

SESSION = "claude-test-session"
ERROR_TEXT = "API Error: provider temporarily unavailable"


def _user(uuid: str = "user-1") -> dict:
    return {
        "type": "user",
        "uuid": uuid,
        "sessionId": SESSION,
        "message": {"role": "user", "content": "Write a short note."},
    }


def _api_error(uuid: str = "error-1", parent: str = "user-1") -> dict:
    return {
        "type": "assistant",
        "uuid": uuid,
        "parentUuid": parent,
        "sessionId": SESSION,
        "isApiErrorMessage": True,
        "message": {"role": "assistant", "content": [{"type": "text", "text": ERROR_TEXT}]},
    }


def _write(path: Path, rows: list[dict]) -> Path:
    path.write_text("".join(json.dumps(row) + "\n" for row in rows))
    return path


def _response(source: str) -> str:
    return "resp_claude_" + hashlib.sha256(source.encode()).hexdigest()[:32]


def _evidence(path: Path, **overrides) -> dict | None:
    options = {
        "error": "overloaded",
        "transcript_path": path,
        "external_session_id": SESSION,
        "response_id": _response("error-1"),
        "last_assistant_message": ERROR_TEXT,
        "model": "approved-model",
    }
    options.update(overrides)
    return claude_failure_evidence(**options)


@pytest.fixture(autouse=True)
def _isolated_bridge(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("omnigent.claude_native_bridge._TRUSTED_PARENT", tmp_path)
    monkeypatch.setattr("omnigent.claude_native_bridge._BRIDGE_ROOT", tmp_path)


def test_evidence_matches_real_first_assistant_response_identity(tmp_path: Path) -> None:
    path = _write(tmp_path / "transcript.jsonl", [_user(), _api_error(), _api_error("error-2")])
    _, response_id, _ = read_transcript_items_since(path, 0, agent_name="reader")
    assert response_id == _response("error-1")
    assert response_id != _response("user-1")
    evidence = _evidence(path, response_id=response_id)
    assert evidence == {
        "harness": "claude-native",
        "turn_id": "user-1",
        "external_session_id": SESSION,
        "kind": "provider_unavailable",
        "before_work": True,
        "model": "approved-model",
    }


@pytest.mark.parametrize("error", ["authentication_failed", "permission_denied", "unknown", None])
def test_nonavailability_error_never_allows_replay(tmp_path: Path, error: str | None) -> None:
    path = _write(tmp_path / "transcript.jsonl", [_user(), _api_error()])
    assert _evidence(path, error=error) is None


@pytest.mark.parametrize(
    "variant",
    [
        "ordinary_assistant",
        "tool",
        "reasoning",
        "new_user",
        "tool_result",
        "malformed",
        "missing_parent",
        "wrong_parent",
        "wrong_session",
        "duplicate_user",
        "empty_error",
        "meta_user",
        "compaction",
        "unknown_record",
    ],
)
def test_work_or_ambiguous_turn_never_allows_replay(tmp_path: Path, variant: str) -> None:
    rows = [_user(), _api_error()]
    if variant == "ordinary_assistant":
        rows[1].pop("isApiErrorMessage")
    elif variant in ("tool", "reasoning"):
        rows[1]["message"]["content"] = [
            {
                "type": "tool_use" if variant == "tool" else "thinking",
                "text": "work",
            }
        ]
    elif variant == "new_user":
        rows.append(_user("user-2"))
    elif variant == "tool_result":
        result = _user("result-1")
        result["message"]["content"] = [{"type": "tool_result", "tool_use_id": "tool-1"}]
        rows.append(result)
    elif variant == "malformed":
        rows[1]["message"]["content"] = ["text"]
    elif variant == "missing_parent":
        rows[1].pop("parentUuid")
    elif variant == "wrong_parent":
        rows[1]["parentUuid"] = "earlier-turn-user"
    elif variant == "wrong_session":
        rows[0]["sessionId"] = "other-session"
    elif variant == "duplicate_user":
        rows.insert(0, deepcopy(rows[0]))
    elif variant == "empty_error":
        rows[1]["message"]["content"] = []
    elif variant == "meta_user":
        rows[0]["isMeta"] = True
    elif variant == "compaction":
        rows[0]["isCompactSummary"] = True
    else:
        rows.append({"type": "unknown"})
    path = _write(tmp_path / "transcript.jsonl", rows)
    assert _evidence(path) is None


@pytest.mark.parametrize(
    "response_id", [None, "unrelated-response", _response("user-1"), _response("error-2")]
)
def test_other_response_identity_cannot_authorize_replay(
    tmp_path: Path, response_id: str | None
) -> None:
    path = _write(tmp_path / "transcript.jsonl", [_user(), _api_error(), _api_error("error-2")])
    assert _evidence(path, response_id=response_id) is None


def test_actual_work_before_api_error_cannot_hide_behind_error_message(tmp_path: Path) -> None:
    work = _api_error("work-1")
    work.pop("isApiErrorMessage")
    work["message"]["content"] = [{"type": "text", "text": "I changed the document."}]
    path = _write(tmp_path / "transcript.jsonl", [_user(), work, _api_error(parent="work-1")])
    assert _evidence(path, response_id=_response("work-1")) is None


def test_hook_message_requires_exact_proven_api_error_text(tmp_path: Path) -> None:
    path = _write(tmp_path / "transcript.jsonl", [_user(), _api_error()])
    assert _evidence(path, last_assistant_message="I updated the file.") is None
    assert _evidence(path, last_assistant_message=None) is not None


def test_no_assistant_requires_positive_user_identity(tmp_path: Path) -> None:
    path = _write(tmp_path / "transcript.jsonl", [_user()])
    assert _evidence(path, response_id=None, last_assistant_message=None) is None
    assert (
        _evidence(path, response_id=_response("user-1"), last_assistant_message=None) is not None
    )


@pytest.mark.parametrize("raw", [b'{"type":"user"}', b"{broken}\n", b"null\n", b"\xff\n"])
def test_incomplete_or_malformed_transcript_never_proves_no_work(
    tmp_path: Path, raw: bytes
) -> None:
    path = tmp_path / "transcript.jsonl"
    path.write_bytes(raw)
    assert _evidence(path) is None


@pytest.mark.asyncio
@pytest.mark.parametrize("work_before_error", [False, True])
async def test_real_transcript_and_stopfailure_forwarding_propagates_only_safe_evidence(
    tmp_path: Path,
    work_before_error: bool,
) -> None:
    rows = [_user()]
    if work_before_error:
        work = _api_error("work-1")
        work.pop("isApiErrorMessage")
        work["message"]["content"] = [{"type": "text", "text": "Already wrote something."}]
        rows.append(work)
    rows.append(_api_error(parent="work-1" if work_before_error else "user-1"))
    transcript = _write(tmp_path / "transcript.jsonl", rows)
    bridge_dir = tmp_path / "bridge"
    record_hook_event(
        bridge_dir,
        {
            "hook_event_name": "StopFailure",
            "session_id": SESSION,
            "transcript_path": str(transcript),
            "error": "overloaded",
            "error_details": "Provider unavailable",
            "last_assistant_message": ERROR_TEXT,
        },
    )
    posts = []

    def handler(request: httpx.Request) -> httpx.Response:
        posts.append(json.loads(request.content))
        return httpx.Response(200, json={})

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler), base_url="http://test"
    ) as client:
        dedupe = forwarder._ForwardDedupeState()
        state = await forwarder._forward_available_items(
            client=client,
            session_id="conv-test",
            bridge_dir=bridge_dir,
            agent_name="reader",
            state=forwarder.TranscriptForwardState(transcript, 0),
            retry_tracker=forwarder._PostRetryTracker(),
            dedupe=dedupe,
        )
        # Resume history may retain the previous model before any new output.
        dedupe.observed_model = "previous-model"
        await forwarder._forward_available_status_events(
            client=client,
            session_id="conv-test",
            bridge_dir=bridge_dir,
            state=forwarder.HookForwardState(event_cursor=0, byte_offset=0),
            retry_tracker=forwarder._PostRetryTracker(),
            dedupe=dedupe,
            task_subjects={},
            task_statuses={},
            task_order=[],
            response_id=state.current_response_id,
        )
    statuses = [post["data"] for post in posts if post.get("type") == "external_session_status"]
    assert len(statuses) == 1
    status = statuses[0]
    assert status["status"] == "failed"
    assert status["response_id"] == _response("work-1" if work_before_error else "error-1")
    assert status["output"] == "Provider unavailable"
    if work_before_error:
        assert "native_failure" not in status
    else:
        assert status["native_failure"]["turn_id"] == "user-1"
        assert status["native_failure"]["before_work"] is True
        assert "model" not in status["native_failure"]
