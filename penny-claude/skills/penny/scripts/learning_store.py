#!/usr/bin/env python3
"""One local, append-only Penny learning log, shared by every host.

This script validates records and state transitions, not their truth: curator
identity, user approval, test execution and semantic generalization are reported
by the caller. It never calls a model or promotes a proposal automatically.
Use a local filesystem; advisory flock does not make an arbitrary network share
safe. Do not edit or replace the log while clients are using it.
"""

from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys
import uuid


SCHEMA_VERSION = 1
MAX_LOG_BYTES = 16 * 1024 * 1024
CURATOR_MODELS = frozenset({"gpt-6-astra", "claude-fable-5-1"})
COMMANDS = ("feedback", "propose", "accept", "reject", "revoke")
IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")
REPORTED_EVIDENCE = (
    "Model identity, test results, approval and generalization are caller-reported, "
    "not independently verified by this store. Pending feedback and proposals "
    "are data, not accepted writing instructions."
)


class StoreError(ValueError):
    """Invalid input, corrupt log, unsafe path, or invalid state transition."""


def _text(value, name, *, empty=False, limit=8192):
    if not isinstance(value, str) or (not empty and not value.strip()):
        raise StoreError(f"{name} must be a nonempty string")
    if len(value) > limit or "\x00" in value:
        raise StoreError(f"{name} is too long or contains a NUL")
    return value


def _identifier(value, name):
    if not isinstance(value, str) or not IDENTIFIER.fullmatch(value):
        raise StoreError(f"{name} must be a 1-128 character identifier")
    return value


def _object(value, name, required=(), optional=()):
    if not isinstance(value, dict):
        raise StoreError(f"{name} must be an object")
    missing = set(required) - value.keys()
    unknown = value.keys() - set(required) - set(optional)
    if missing or unknown:
        raise StoreError(
            f"{name}: missing fields {sorted(missing)}, unknown fields {sorted(unknown)}"
        )
    return value


def _scope(value, name="scope"):
    if not isinstance(value, dict) or len(value) > 16:
        raise StoreError(f"{name} must be an object with at most 16 string dimensions")
    for key, item in value.items():
        _identifier(key, f"{name} key")
        _text(item, f"{name}.{key}", limit=256)
    return dict(value)


def _test(value, name):
    _object(value, name, ("status", "scenario", "expected", "observed"))
    if value["status"] not in ("pass", "fail", "untested"):
        raise StoreError(f"{name}.status must be pass, fail or untested")
    for field in ("scenario", "expected", "observed"):
        _text(value[field], f"{name}.{field}", empty=(
            field == "observed" and value["status"] == "untested"
        ))
    return dict(value)


def _payload(kind, data):
    """Validate and normalize a command-specific payload, without state access."""
    if kind == "feedback":
        _object(data, kind, ("summary", "reason"), ("scope",))
        return {
            "summary": _text(data["summary"], "summary"),
            "reason": _text(data["reason"], "reason"),
            "scope": _scope(data.get("scope", {})),
        }
    if kind == "propose":
        required = ("feedback_ids", "lesson", "applies_when", "does_not_apply",
                    "dimension", "curator_model", "tests")
        _object(data, kind, required, ("scope", "supersedes"))
        ids = data["feedback_ids"]
        if not isinstance(ids, list) or not ids or len(ids) > 100:
            raise StoreError("feedback_ids must contain 1-100 feedback event IDs")
        for event_id in ids:
            _identifier(event_id, "feedback_ids entry")
        if len(set(ids)) != len(ids):
            raise StoreError("feedback_ids must not contain duplicates")
        if not isinstance(data["curator_model"], str) or data["curator_model"] not in CURATOR_MODELS:
            raise StoreError("curator_model must be gpt-6-astra or claude-fable-5-1")
        tests = _object(data["tests"], "tests", ("transfer", "boundary"))
        result = {
            "feedback_ids": list(ids),
            "lesson": _text(data["lesson"], "lesson"),
            "applies_when": _text(data["applies_when"], "applies_when"),
            "does_not_apply": _text(data["does_not_apply"], "does_not_apply"),
            "dimension": _identifier(data["dimension"], "dimension"),
            "scope": _scope(data.get("scope", {})),
            "curator_model": data["curator_model"],
            "tests": {key: _test(tests[key], f"tests.{key}")
                      for key in ("transfer", "boundary")},
        }
        if "supersedes" in data:
            result["supersedes"] = _identifier(data["supersedes"], "supersedes")
        return result
    if kind in ("accept", "reject", "revoke"):
        explanation = "approval" if kind == "accept" else "reason"
        _object(data, kind, ("proposal_id", explanation))
        return {
            "proposal_id": _identifier(data["proposal_id"], "proposal_id"),
            explanation: _text(data[explanation], explanation),
        }
    raise StoreError(f"Unknown event type: {kind}")


def _empty():
    return {"events": [], "by_id": {}, "feedback": {}, "proposals": {},
            "revision": hashlib.sha256(b"").hexdigest(), "log_bytes": 0}


def _apply(state, event):
    """Validate and replay one complete event. Does not mutate the log file."""
    _object(event, "event", ("schema_version", "event_id", "timestamp", "source_host", "type", "data"))
    if type(event["schema_version"]) is not int or event["schema_version"] != SCHEMA_VERSION:
        raise StoreError("Unsupported event schema_version")
    event_id = _identifier(event["event_id"], "event_id")
    if event_id in state["by_id"]:
        raise StoreError(f"Duplicate event_id in log: {event_id}")
    _identifier(event["source_host"], "source_host")
    try:
        timestamp = datetime.fromisoformat(event["timestamp"].replace("Z", "+00:00"))
        if timestamp.tzinfo is None:
            raise ValueError("timezone missing")
    except (AttributeError, TypeError, ValueError) as exc:
        raise StoreError("timestamp must be a timezone-aware ISO datetime") from exc
    kind = event["type"]
    data = _payload(kind, event["data"])
    if data != event["data"]:
        raise StoreError("Log event is not in canonical schema form")

    if kind == "feedback":
        state["feedback"][event_id] = event
    elif kind == "propose":
        for feedback_id in data["feedback_ids"]:
            if feedback_id not in state["feedback"]:
                raise StoreError(f"Unknown feedback event: {feedback_id}")
        if "supersedes" in data:
            prior = state["proposals"].get(data["supersedes"])
            if prior is None or prior["status"] != "active":
                raise StoreError("supersedes must identify an active accepted proposal")
            prior_data = prior["event"]["data"]
            if (prior_data["dimension"], prior_data["scope"]) != (data["dimension"], data["scope"]):
                raise StoreError("Supersession must preserve dimension and exact scope")
        state["proposals"][event_id] = {"event": event, "status": "pending"}
    else:
        proposal_id = data["proposal_id"]
        proposal = state["proposals"].get(proposal_id)
        if proposal is None:
            raise StoreError(f"Unknown proposal: {proposal_id}")
        expected = "active" if kind == "revoke" else "pending"
        if proposal["status"] != expected:
            raise StoreError(f"{kind} requires a {expected} proposal; found {proposal['status']}")
        if kind == "accept":
            proposed = proposal["event"]["data"]
            if any(test["status"] != "pass" for test in proposed["tests"].values()):
                raise StoreError("Acceptance requires passing reported transfer and boundary tests")
            prior_id = proposed.get("supersedes")
            if prior_id:
                prior = state["proposals"][prior_id]
                if prior["status"] != "active":
                    raise StoreError("Superseded lesson changed since proposal; propose again")
                prior["status"] = "superseded"
                prior["superseded_by"] = proposal_id
            proposal["status"] = "active"
            proposal["accepted_event_id"] = event_id
        else:
            proposal["status"] = "rejected" if kind == "reject" else "revoked"
        proposal["decision_event_id"] = event_id
    state["events"].append(event)
    state["by_id"][event_id] = event


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise StoreError(f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def _decode(text):
    def invalid_constant(value):
        raise StoreError(f"Non-finite JSON value: {value}")
    try:
        return json.loads(text, object_pairs_hook=_unique_object,
                          parse_constant=invalid_constant)
    except (json.JSONDecodeError, UnicodeError) as exc:
        raise StoreError("Invalid JSON") from exc


def _read_locked(fd):
    if os.fstat(fd).st_size > MAX_LOG_BYTES:
        raise StoreError("Learning log exceeds the 16 MiB safety limit; log left untouched")
    os.lseek(fd, 0, os.SEEK_SET)
    chunks = []
    while True:
        chunk = os.read(fd, 65536)
        if not chunk:
            break
        chunks.append(chunk)
    raw = b"".join(chunks)
    if raw and not raw.endswith(b"\n"):
        raise StoreError("Truncated log: final record has no newline; log left untouched")
    state = _empty()
    state["revision"] = hashlib.sha256(raw).hexdigest()
    state["log_bytes"] = len(raw)
    for number, line in enumerate(raw.splitlines(), 1):
        try:
            _apply(state, _decode(line.decode("utf-8")))
        except (StoreError, UnicodeError) as exc:
            raise StoreError(f"Corrupt log at line {number}: {exc}; log left untouched") from exc
    return state


@contextmanager
def _locked(path, *, write):
    path = Path(path).expanduser()
    if write:
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    flags = os.O_RDWR | os.O_APPEND | os.O_CREAT if write else os.O_RDONLY
    flags |= getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_CLOEXEC", 0)
    try:
        fd = os.open(path, flags, 0o600)
    except FileNotFoundError:
        if not write:
            yield None
            return
        raise
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
            raise StoreError("Learning log must be a regular file, not a symlink or hard link")
        if info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) & 0o077:
            raise StoreError("Learning log must be owned by this user and private (mode 0600)")
        fcntl.flock(fd, fcntl.LOCK_EX if write else fcntl.LOCK_SH)
        try:
            yield fd
        finally:
            fcntl.flock(fd, fcntl.LOCK_UN)
    finally:
        os.close(fd)


def append_event(log_path, command, payload):
    """Append one validated event, or return a prior matching idempotent event."""
    if command not in COMMANDS:
        raise StoreError(f"Unknown command: {command}")
    if not isinstance(payload, dict):
        raise StoreError("Input must be a JSON object")
    source_host = _identifier(payload.get("source_host"), "source_host")
    event_id = _identifier(payload.get("event_id", str(uuid.uuid4())), "event_id")
    data = _payload(command, {key: value for key, value in payload.items()
                              if key not in ("source_host", "event_id")})
    with _locked(log_path, write=True) as fd:
        state = _read_locked(fd)
        previous = state["by_id"].get(event_id)
        if previous:
            if (previous["type"], previous["source_host"], previous["data"]) != (command, source_host, data):
                raise StoreError("event_id was already used with different content")
            return {"event": previous, "replayed": True, "evidence_note": REPORTED_EVIDENCE}
        event = {
            "schema_version": SCHEMA_VERSION,
            "event_id": event_id,
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "source_host": source_host,
            "type": command,
            "data": data,
        }
        _apply(state, event)
        encoded = (json.dumps(event, ensure_ascii=False, sort_keys=True,
                              separators=(",", ":"), allow_nan=False) + "\n").encode("utf-8")
        if state["log_bytes"] + len(encoded) > MAX_LOG_BYTES:
            raise StoreError("Append would exceed the 16 MiB safety limit; log left untouched")
        remaining = memoryview(encoded)
        while remaining:
            count = os.write(fd, remaining)
            if count <= 0:
                raise OSError("Unable to append learning event")
            remaining = remaining[count:]
        os.fsync(fd)
    return {"event": event, "replayed": False, "evidence_note": REPORTED_EVIDENCE}


def _read_state(log_path):
    with _locked(log_path, write=False) as fd:
        return _empty() if fd is None else _read_locked(fd)


def read_events(log_path):
    """Read validated events, holding a shared lock throughout replay."""
    return _read_state(log_path)["events"]


def load_state(log_path, context=None):
    """Return only accepted active lessons with exact matching scope dimensions.

    Omitted context means only unscoped lessons. Prose applicability and boundary
    conditions still require judgment; matching metadata does not prove relevance.
    """
    context = _scope({} if context is None else context, "context")
    state = _read_state(log_path)
    active, scoped_out, pending, resolved = [], [], [], set()
    for proposal_id, item in state["proposals"].items():
        data = item["event"]["data"]
        if item["status"] in ("active", "superseded"):
            resolved.update(data["feedback_ids"])
        if item["status"] == "pending":
            pending.append({"proposal_id": proposal_id, **data,
                            "source_host": item["event"]["source_host"]})
        if item["status"] != "active":
            continue
        lesson = {"proposal_id": proposal_id,
                  **{key: data[key] for key in ("lesson", "applies_when", "does_not_apply", "dimension", "scope")},
                  "accepted_event_id": item["accepted_event_id"]}
        if all(context.get(key) == value for key, value in data["scope"].items()):
            active.append(lesson)
        else:
            scoped_out.append({"proposal_id": proposal_id, "scope": data["scope"]})
    return {
        "schema_version": SCHEMA_VERSION,
        "revision": state["revision"],
        "log_bytes": state["log_bytes"],
        "capacity_bytes": MAX_LOG_BYTES,
        "event_count": len(state["events"]),
        "context": context,
        "active_lessons": active,
        "scoped_out": scoped_out,
        "pending_feedback": [event for event_id, event in state["feedback"].items()
                             if event_id not in resolved],
        "pending_proposals": pending,
        "proposal_statuses": {key: item["status"] for key, item in state["proposals"].items()},
        "evidence_note": REPORTED_EVIDENCE,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("load", "events", *COMMANDS))
    parser.add_argument("--log", type=Path, default=Path.home() / ".penny" / "learning.jsonl")
    parser.add_argument("--input", type=Path, help="JSON payload file; mutations otherwise read stdin")
    args = parser.parse_args(argv)
    try:
        if args.command == "events":
            if args.input:
                raise StoreError("events does not take an input payload")
            result = {"events": read_events(args.log), "evidence_note": REPORTED_EVIDENCE}
        elif args.command == "load":
            # No stdin read for load: it must not hang when called at turn start.
            payload = _decode(args.input.read_text(encoding="utf-8")) if args.input else {}
            _object(payload, "load input", (), ("context",))
            result = load_state(args.log, payload.get("context", {}))
        else:
            payload = _decode(args.input.read_text(encoding="utf-8") if args.input else sys.stdin.read())
            result = append_event(args.log, args.command, payload)
        print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False))
        return 0
    except (StoreError, OSError, UnicodeError) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
