"""Isolated behavior tests: no writes to the user's actual learning log."""

import importlib.util
import hashlib
import json
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from concurrent.futures import ThreadPoolExecutor


SCRIPT = Path(__file__).resolve().parents[1] / "skills" / "penny" / "scripts" / "learning_store.py"
SPEC = importlib.util.spec_from_file_location("penny_learning_store", SCRIPT)
store = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(store)


class LearningStoreTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="penny-learning-test-")
        self.addCleanup(self.temporary.cleanup)
        self.log = Path(self.temporary.name) / "shared" / "learning.jsonl"

    def call(self, command, payload=None, ok=True, input_file=False):
        args = [sys.executable, str(SCRIPT), command, "--log", str(self.log)]
        text = json.dumps(payload) if payload is not None else None
        if input_file:
            path = Path(self.temporary.name) / "input.json"
            path.write_text(text, encoding="utf-8")
            args.extend(["--input", str(path)])
            text = None
        result = subprocess.run(args, input=text, text=True, capture_output=True, timeout=15)
        self.assertEqual(result.returncode, 0 if ok else 2, result.stdout + result.stderr)
        return json.loads(result.stdout if ok else result.stderr)

    def feedback(self, event_id="feedback-1", host="omnigent", **fields):
        return {"event_id": event_id, "source_host": host,
                "summary": "The draft exposed writer checking instructions.",
                "reason": "The reader needs the result, not the writing process.", **fields}

    def proposal(self, event_id="proposal-1", feedback_id="feedback-1", **fields):
        test = {"status": "pass", "scenario": "A generic project update.",
                "expected": "Reader sees the open decision, not review instructions.",
                "observed": "The update states the open decision."}
        return {"event_id": event_id, "source_host": "claude-code",
                "feedback_ids": [feedback_id],
                "lesson": "Apply writer checks without narrating them in reader-facing drafts.",
                "applies_when": "The task is a reader-facing draft.",
                "does_not_apply": "The reader explicitly asks for a review checklist.",
                "dimension": "reader-purpose", "curator_model": "gpt-6-astra",
                "tests": {"transfer": dict(test), "boundary": {**test,
                    "scenario": "A requested review checklist.",
                    "expected": "Keep the requested review instructions.",
                    "observed": "The checklist retains review instructions."}}, **fields}

    def accept(self, proposal_id="proposal-1", event_id="accept-1"):
        return {"event_id": event_id, "source_host": "codex", "proposal_id": proposal_id,
                "approval": "The user explicitly accepted this proposed lesson."}

    def seed(self, **proposal_fields):
        store.append_event(self.log, "feedback", self.feedback())
        store.append_event(self.log, "propose", self.proposal(**proposal_fields))
        store.append_event(self.log, "accept", self.accept())

    def test_missing_log_load_is_empty_and_creates_nothing(self):
        result = self.call("load")
        self.assertEqual(result["active_lessons"], [])
        self.assertEqual(result["event_count"], 0)
        self.assertFalse(self.log.parent.exists())

    def test_three_host_subprocesses_share_state_and_only_accept_promotes(self):
        self.call("feedback", self.feedback(), input_file=True)
        before = self.call("load")
        self.assertEqual(len(before["pending_feedback"]), 1)
        self.assertEqual(before["active_lessons"], [])
        self.call("propose", self.proposal())
        proposed = self.call("load")
        self.assertEqual(len(proposed["pending_proposals"]), 1)
        self.assertEqual(proposed["active_lessons"], [])
        self.call("accept", self.accept())
        after = self.call("load")
        self.assertEqual(len(after["active_lessons"]), 1)
        self.assertEqual(after["pending_feedback"], [])
        self.assertEqual(after["pending_proposals"], [])
        events = self.call("events")["events"]
        self.assertEqual([event["source_host"] for event in events],
                         ["omnigent", "claude-code", "codex"])

    def test_concurrent_subprocess_writes_never_lose_or_interleave_events(self):
        def append(index):
            return self.call("feedback", self.feedback(f"parallel-{index}", f"host-{index % 3}"))
        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(append, range(24)))
        self.assertEqual(len(results), 24)
        events = store.read_events(self.log)
        self.assertEqual(len(events), 24)
        self.assertEqual({event["event_id"] for event in events},
                         {f"parallel-{index}" for index in range(24)})

    def test_idempotency_and_conflicting_reuse(self):
        first = self.call("feedback", self.feedback())
        snapshot = self.log.read_bytes()
        second = self.call("feedback", self.feedback())
        self.assertFalse(first["replayed"])
        self.assertTrue(second["replayed"])
        self.assertEqual(first["event"], second["event"])
        self.call("feedback", self.feedback(reason="A different reason."), ok=False)
        self.call("feedback", self.feedback(host="codex"), ok=False)
        self.assertEqual(self.log.read_bytes(), snapshot)

    def test_concurrent_same_id_appends_once(self):
        def append(_):
            return self.call("feedback", self.feedback())
        with ThreadPoolExecutor(max_workers=6) as pool:
            results = list(pool.map(append, range(12)))
        self.assertEqual(sum(not item["replayed"] for item in results), 1)
        self.assertEqual(len(store.read_events(self.log)), 1)

    def test_corruption_never_overwritten_or_ignored(self):
        self.call("feedback", self.feedback())
        valid = self.log.read_bytes()
        for extra in (b'{"unfinished":', b'not-json\n', b'{}\n', b'\n', b'\xff\n'):
            with self.subTest(extra=extra):
                damaged = valid + extra
                self.log.write_bytes(damaged)
                self.call("load", ok=False)
                self.call("feedback", self.feedback("new"), ok=False)
                self.assertEqual(self.log.read_bytes(), damaged)

    def test_corrupt_historical_reference_and_duplicate_id_are_rejected(self):
        self.seed()
        original = self.log.read_bytes()
        events = [json.loads(line) for line in original.splitlines()]
        for transform in (lambda records: records + [records[0]],
                          lambda records: [records[0], records[2], records[1]]):
            changed = b"".join((json.dumps(event) + "\n").encode() for event in transform(events))
            self.log.write_bytes(changed)
            self.call("load", ok=False)
            self.call("feedback", self.feedback("new"), ok=False)
            self.assertEqual(self.log.read_bytes(), changed)

    def test_accept_unknown_or_missing_approval_is_denied(self):
        self.call("accept", self.accept(), ok=False)
        self.call("feedback", self.feedback())
        self.call("propose", self.proposal())
        snapshot = self.log.read_bytes()
        missing = self.accept()
        missing.pop("approval")
        self.call("accept", missing, ok=False)
        self.call("accept", {**self.accept(), "approval": " "}, ok=False)
        self.assertEqual(self.log.read_bytes(), snapshot)

    def test_failed_and_untested_proposals_cannot_be_accepted(self):
        self.call("feedback", self.feedback())
        for status in ("fail", "untested"):
            for stage in ("transfer", "boundary"):
                with self.subTest(status=status, stage=stage):
                    proposal_id = f"proposal-{status}-{stage}"
                    proposed = self.proposal(proposal_id)
                    proposed["tests"][stage]["status"] = status
                    self.call("propose", proposed)
                    snapshot = self.log.read_bytes()
                    self.call("accept", self.accept(proposal_id, f"accept-{status}-{stage}"), ok=False)
                    self.assertEqual(self.log.read_bytes(), snapshot)
        self.assertEqual(store.load_state(self.log)["active_lessons"], [])

    def test_reject_then_accept_is_denied_and_feedback_stays_pending(self):
        self.call("feedback", self.feedback())
        self.call("propose", self.proposal())
        self.call("reject", {"source_host": "omnigent", "proposal_id": "proposal-1",
                             "reason": "The user declined this lesson."})
        self.call("accept", self.accept(), ok=False)
        result = self.call("load")
        self.assertEqual(result["proposal_statuses"]["proposal-1"], "rejected")
        self.assertEqual(len(result["pending_feedback"]), 1)

    def test_supersession_and_revocation_do_not_resurrect_old_lesson(self):
        self.seed()
        self.call("propose", self.proposal("proposal-2", supersedes="proposal-1",
                   lesson="Keep requested checklists; otherwise apply checks without narrating them."))
        self.call("accept", self.accept("proposal-2", "accept-2"))
        result = self.call("load")
        self.assertEqual([x["proposal_id"] for x in result["active_lessons"]], ["proposal-2"])
        self.assertEqual(result["proposal_statuses"]["proposal-1"], "superseded")
        self.call("revoke", {"source_host": "codex", "proposal_id": "proposal-2",
                             "reason": "User revoked the learned preference."})
        result = self.call("load")
        self.assertEqual(result["active_lessons"], [])
        self.assertEqual(result["proposal_statuses"],
                         {"proposal-1": "superseded", "proposal-2": "revoked"})

    def test_stale_supersession_fails_without_losing_earlier_update(self):
        self.seed()
        self.call("propose", self.proposal("proposal-2", supersedes="proposal-1"))
        self.call("propose", self.proposal("proposal-3", supersedes="proposal-1"))
        self.call("accept", self.accept("proposal-2", "accept-2"))
        snapshot = self.log.read_bytes()
        self.call("accept", self.accept("proposal-3", "accept-3"), ok=False)
        self.assertEqual(self.log.read_bytes(), snapshot)

    def test_scope_exact_match_and_supersession_boundary(self):
        self.seed(scope={"channel": "slack", "purpose": "status"})
        self.assertEqual(self.call("load")["active_lessons"], [])
        context = {"context": {"channel": "slack", "purpose": "status", "audience": "team"}}
        self.assertEqual(len(self.call("load", context, input_file=True)["active_lessons"]), 1)
        self.assertEqual(store.load_state(self.log, {"channel": "email", "purpose": "status"})["active_lessons"], [])
        self.call("propose", self.proposal("proposal-2", supersedes="proposal-1"), ok=False)
        self.call("propose", self.proposal("proposal-2", supersedes="proposal-1",
                  scope={"channel": "slack", "purpose": "status"}, dimension="brevity"), ok=False)

    def test_private_new_file_and_parent_permissions(self):
        self.call("feedback", self.feedback())
        self.assertEqual(stat.S_IMODE(self.log.stat().st_mode), 0o600)
        self.assertEqual(stat.S_IMODE(self.log.parent.stat().st_mode), 0o700)

    def test_public_log_and_links_are_refused(self):
        self.call("feedback", self.feedback())
        self.log.chmod(0o644)
        self.call("load", ok=False)
        self.log.chmod(0o600)
        target = self.log.with_name("target.jsonl")
        self.log.rename(target)
        self.log.symlink_to(target)
        self.call("load", ok=False)
        self.call("feedback", self.feedback("next"), ok=False)
        self.assertEqual(len(target.read_text().splitlines()), 1)

    def test_unknown_raw_data_fields_and_unapproved_model_are_refused(self):
        self.call("feedback", self.feedback(raw_example="A private source message."), ok=False)
        self.assertFalse(self.log.exists())
        self.call("feedback", self.feedback())
        self.call("propose", self.proposal(curator_model="unknown-model"), ok=False)
        proposed = self.proposal()
        proposed["tests"].pop("boundary")
        self.call("propose", proposed, ok=False)

    def test_duplicate_json_keys_are_rejected(self):
        result = subprocess.run([sys.executable, str(SCRIPT), "feedback", "--log", str(self.log)],
                                input='{"source_host":"codex","source_host":"other"}',
                                text=True, capture_output=True, timeout=15)
        self.assertEqual(result.returncode, 2)
        self.assertIn("Duplicate JSON key", result.stderr)
        self.assertFalse(self.log.exists())

    def test_revision_identifies_exact_log_content(self):
        empty = self.call("load")
        self.assertEqual(empty["revision"], hashlib.sha256(b"").hexdigest())
        self.call("feedback", self.feedback())
        loaded = self.call("load")
        self.assertEqual(loaded["revision"], hashlib.sha256(self.log.read_bytes()).hexdigest())
        self.assertEqual(loaded["log_bytes"], len(self.log.read_bytes()))
        self.assertNotEqual(empty["revision"], loaded["revision"])
        self.assertEqual(loaded["capacity_bytes"], 16 * 1024 * 1024)

    def test_size_cap_rejects_append_without_changing_existing_data(self):
        self.call("feedback", self.feedback())
        snapshot = self.log.read_bytes()
        with patch.object(store, "MAX_LOG_BYTES", len(snapshot) + 1):
            with self.assertRaises(store.StoreError):
                store.append_event(self.log, "feedback", self.feedback("next"))
            self.assertEqual(store.load_state(self.log)["log_bytes"], len(snapshot))
        self.assertEqual(self.log.read_bytes(), snapshot)
        with patch.object(store, "MAX_LOG_BYTES", len(snapshot) - 1):
            with self.assertRaises(store.StoreError):
                store.load_state(self.log)
        self.assertEqual(self.log.read_bytes(), snapshot)

    def test_malformed_model_value_is_cleanly_rejected(self):
        self.call("feedback", self.feedback())
        result = self.call("propose", self.proposal(curator_model=["gpt-6-astra"]), ok=False)
        self.assertIn("curator_model", result["error"])


if __name__ == "__main__":
    unittest.main()
