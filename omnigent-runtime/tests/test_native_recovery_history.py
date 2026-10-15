"""Recovery carries only history preceding the one input it will retry."""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest

from omnigent import claude_native, codex_native

THREAD_ID = "019e96aa-0be2-7343-8d3b-6f914d60936b"


def _message(item_id: str, text: str) -> dict:
    return {
        "id": item_id,
        "type": "message",
        "role": "user",
        "content": [{"type": "input_text", "text": text}],
    }


@pytest.fixture(autouse=True)
def _isolated_native_storage(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(claude_native, "_CLAUDE_PROJECTS_DIR", tmp_path / "claude-projects")
    monkeypatch.setattr("omnigent.claude_native_bridge._TRUSTED_PARENT", tmp_path)
    monkeypatch.setattr("omnigent.claude_native_bridge._BRIDGE_ROOT", tmp_path / "claude-bridge")


async def _rebuild(harness: str, client: httpx.AsyncClient, tmp_path: Path) -> Path | None:
    kwargs = {
        "session_id": "conv_recovery",
        "external_session_id": THREAD_ID,
        "workspace": tmp_path / "workspace",
        "history_before_item_id": "retry-input",
    }
    if harness == "codex":
        return await codex_native._ensure_local_codex_resume_rollout(
            client,
            **kwargs,
            codex_home=tmp_path / "codex-home",
            model_provider="openai",
            codex_path=None,
        )
    return await claude_native._ensure_local_claude_resume_transcript(client, **kwargs)


@pytest.mark.asyncio
@pytest.mark.parametrize("harness", ["codex", "claude"])
async def test_recovery_history_is_exclusive_after_complete_paginated_fetch(
    harness: str,
    tmp_path: Path,
) -> None:
    pages = [
        [_message("prior-input", "earlier completed context")],
        [
            _message("retry-input", "retry exactly once"),
            _message("later-input", "must not leak into recovered history"),
        ],
    ]
    requests = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        assert request.url.path == "/v1/sessions/conv_recovery/items"
        page = 0 if request.url.params.get("after") is None else 1
        return httpx.Response(
            200,
            json={
                "data": pages[page],
                "has_more": page == 0,
                "last_id": "prior-input",
            },
        )

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler), base_url="http://test"
    ) as client:
        path = await _rebuild(harness, client, tmp_path)

    assert len(requests) == 2
    assert path is not None
    text = path.read_text()
    assert "earlier completed context" in text
    assert "retry exactly once" not in text
    assert "must not leak" not in text
    assert all(isinstance(json.loads(line), dict) for line in text.splitlines())


@pytest.mark.asyncio
@pytest.mark.parametrize("harness", ["codex", "claude"])
@pytest.mark.parametrize("duplicate", [False, True])
async def test_recovery_rejects_missing_or_ambiguous_boundary_without_writing(
    harness: str,
    duplicate: bool,
    tmp_path: Path,
) -> None:
    items = [_message("prior-input", "earlier context")]
    if duplicate:
        items += [_message("retry-input", "one"), _message("retry-input", "two")]
    transport = httpx.MockTransport(
        lambda request: httpx.Response(200, json={"data": items, "has_more": False})
    )
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        with pytest.raises(ValueError, match="exactly one committed item"):
            await _rebuild(harness, client, tmp_path)
    assert not list(tmp_path.rglob("*.jsonl"))


@pytest.mark.asyncio
@pytest.mark.parametrize("harness", ["codex", "claude"])
async def test_empty_exclusive_prefix_requires_fresh_launch_without_writing(
    harness: str,
    tmp_path: Path,
) -> None:
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            200,
            json={
                "data": [_message("retry-input", "first task input")],
                "has_more": False,
            },
        )
    )
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        assert await _rebuild(harness, client, tmp_path) is None
    assert not list(tmp_path.rglob("*.jsonl"))


@pytest.mark.asyncio
async def test_bounded_codex_recovery_rejects_existing_unbounded_rollout(tmp_path: Path) -> None:
    existing = codex_native._codex_resume_rollout_path(tmp_path / "codex-home", THREAD_ID)
    existing.parent.mkdir(parents=True)
    original = b'{"type":"response_item","payload":{"text":"failed input"}}\n'
    existing.write_bytes(original)

    def unexpected_request(request: httpx.Request) -> httpx.Response:
        raise AssertionError("Existing rollout must be rejected before use")

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(unexpected_request), base_url="http://test"
    ) as client:
        with pytest.raises(ValueError, match="fresh external session id"):
            await _rebuild("codex", client, tmp_path)
    assert existing.read_bytes() == original


@pytest.mark.asyncio
async def test_bounded_claude_recovery_never_uses_stale_local_transcript(tmp_path: Path) -> None:
    existing = (
        claude_native._claude_project_dir_for_cwd(tmp_path / "workspace") / f"{THREAD_ID}.jsonl"
    )
    existing.parent.mkdir(parents=True)
    original = b'{"type":"user","message":{"role":"user","content":"failed input"}}\n'
    existing.write_bytes(original)
    transport = httpx.MockTransport(
        lambda request: httpx.Response(500, json={"error": "unavailable"})
    )
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        with pytest.raises(claude_native._ResumeHistoryUnavailableError):
            await _rebuild("claude", client, tmp_path)
    assert existing.read_bytes() == original
