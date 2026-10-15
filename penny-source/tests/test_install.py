"""Exercise install boundaries using temporary paths and the real Omnigent stores."""

import hashlib
import io
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.manage import (
    SKILL, VERIFIED_RUNTIME, VERIFIED_SCHEMA, build_bundle, install_skills,
    register_new, update_existing, validate_bundle, verify_update_runtime,
)


CATALOG = Path(__file__).parent / "fixtures/model_catalog.json"
CLAUDE_CATALOG = Path(__file__).parent / "fixtures/claude_model_catalog.json"


class SkillInstallTests(unittest.TestCase):
    def test_shared_source_and_idempotent_install(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            first = install_skills(home)
            self.assertEqual(first, install_skills(home))
            for name in first["installed"]:
                self.assertEqual(Path(name).resolve(), SKILL)

    def test_collision_does_not_partially_install(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            existing = home / ".claude/skills/penny"
            existing.mkdir(parents=True)
            with self.assertRaises(FileExistsError):
                install_skills(home)
            self.assertFalse((home / ".agents/skills/penny").exists())
            self.assertTrue(existing.is_dir())


class BundleTests(unittest.TestCase):
    def test_bundle_and_archive_load_in_installed_runtime(self):
        from omnigent.errors import OmnigentError
        from omnigent.server.app import _tar_gz_dir
        from omnigent.server.bundles import validate_agent_bundle

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "penny"
            build_bundle(root, model_catalog=CATALOG, claude_model_catalog=CLAUDE_CATALOG)
            manifest = json.loads((root / "generation.json").read_text())
            self.assertEqual(manifest["model_catalogs"]["codex-native"]["source"], "host_model_catalog")
            self.assertNotIn("path", manifest["model_catalogs"]["codex-native"])
            self.assertTrue(validate_bundle(root)["valid"])
            self.assertEqual(_tar_gz_dir(root), _tar_gz_dir(root))
            # Local operator-authored bundles can use this fixed deny policy.
            # Untrusted HTTP uploads require an administrator-registered handler.
            validate_agent_bundle(_tar_gz_dir(root), enforce_handler_allowlist=False)
            with self.assertRaisesRegex(OmnigentError, "not a registered policy handler"):
                validate_agent_bundle(_tar_gz_dir(root))
            build_bundle(root, model_catalog=CATALOG, claude_model_catalog=CLAUDE_CATALOG)

    def test_different_existing_bundle_is_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "penny"
            root.mkdir()
            marker = root / "keep.txt"
            marker.write_text("existing work")
            with self.assertRaises(FileExistsError):
                build_bundle(root, model_catalog=CATALOG, claude_model_catalog=CLAUDE_CATALOG)
            self.assertEqual(marker.read_text(), "existing work")


class RegistrationTests(unittest.TestCase):
    def test_corrupt_registered_artifact_is_rejected_and_preserved(self):
        from omnigent.runtime.agent_cache import AgentCache
        from omnigent.stores.agent_store.sqlalchemy_store import SqlAlchemyAgentStore
        from omnigent.stores.artifact_store.local import LocalArtifactStore

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            store = SqlAlchemyAgentStore(f"sqlite:///{root / 'test.db'}")
            artifacts = LocalArtifactStore(str(root / "artifacts"))
            cache = AgentCache(artifacts, root / "cache")
            payload = b"synthetic registration bundle"
            registered = register_new(store, artifacts, cache, payload)
            location = store.get_by_name("penny").bundle_location
            artifacts.put(location, b"corrupted existing bytes")
            with self.assertRaisesRegex(RuntimeError, "stored hash"):
                register_new(store, artifacts, cache, payload)
            self.assertEqual(artifacts.get(location), b"corrupted existing bytes")
            self.assertEqual(store.get_by_name("penny").version, registered["version"])

    def test_occupied_artifact_key_is_not_overwritten_or_registered(self):
        from omnigent.db.utils import builtin_agent_id
        from omnigent.runtime.agent_cache import AgentCache
        from omnigent.stores.agent_store.sqlalchemy_store import SqlAlchemyAgentStore
        from omnigent.stores.artifact_store.local import LocalArtifactStore

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            store = SqlAlchemyAgentStore(f"sqlite:///{root / 'test.db'}")
            artifacts = LocalArtifactStore(str(root / "artifacts"))
            cache = AgentCache(artifacts, root / "cache")
            payload = b"synthetic registration bundle"
            location = f"{builtin_agent_id('penny')}/{hashlib.sha256(payload).hexdigest()}"
            artifacts.put(location, b"existing different bytes")
            with self.assertRaisesRegex(RuntimeError, "occupied"):
                register_new(store, artifacts, cache, payload)
            self.assertEqual(artifacts.get(location), b"existing different bytes")
            self.assertIsNone(store.get_by_name("penny"))

    def test_new_registration_preserves_existing_agents_and_repeats(self):
        from omnigent.runtime.agent_cache import AgentCache
        from omnigent.server.app import _tar_gz_dir
        from omnigent.stores.agent_store.sqlalchemy_store import SqlAlchemyAgentStore
        from omnigent.stores.artifact_store.local import LocalArtifactStore

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            store = SqlAlchemyAgentStore(f"sqlite:///{root / 'test.db'}")
            for number, name in enumerate(("alpha", "beta", "gamma", "delta"), 1):
                store.create(f"{number:032x}", name, f"existing/{name}")
            before = {a.id: (a.name, a.version, a.bundle_location) for a in store.list().data}
            artifacts = LocalArtifactStore(str(root / "artifacts"))
            cache = AgentCache(artifacts, root / "cache")
            bundle = root / "penny"
            build_bundle(bundle, model_catalog=CATALOG, claude_model_catalog=CLAUDE_CATALOG)
            payload = _tar_gz_dir(bundle)
            first = register_new(store, artifacts, cache, payload)
            self.assertEqual(first["action"], "registered_new")
            self.assertEqual(register_new(store, artifacts, cache, payload)["action"], "already_registered")
            after = {a.id: (a.name, a.version, a.bundle_location) for a in store.list().data if a.name != "penny"}
            self.assertEqual(before, after)
            with self.assertRaises(RuntimeError):
                register_new(store, artifacts, cache, payload + b"different")
            self.assertEqual(store.get_by_name("penny").version, 1)


class UpdateTests(unittest.TestCase):
    def setUp(self):
        from omnigent.db.utils import builtin_agent_id
        from omnigent.stores.agent_store.sqlalchemy_store import SqlAlchemyAgentStore
        from omnigent.stores.artifact_store.local import LocalArtifactStore

        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.database = self.root / "test.db"
        self.uri = f"sqlite:///{self.database}"
        self.store = SqlAlchemyAgentStore(self.uri)
        self.artifacts = LocalArtifactStore(str(self.root / "artifacts"))
        self.agent_id = builtin_agent_id("penny")
        self.old_payload = b"previous synthetic bundle"
        self.old_hash = hashlib.sha256(self.old_payload).hexdigest()
        self.old_location = f"{self.agent_id}/{self.old_hash}"
        self.artifacts.put(self.old_location, self.old_payload)
        self.store.create(self.agent_id, "penny", self.old_location)
        for number, name in enumerate(("alpha", "beta", "gamma", "delta"), 1):
            self.store.create(f"{number:032x}", name, f"existing/{name}")
        with sqlite3.connect(self.database) as connection:
            conversation_id = bytes.fromhex("a" * 32)
            connection.execute(
                "INSERT INTO conversations (id, created_at, updated_at, title, "
                "root_conversation_id, next_position, workspace_id, agent_id, archived) "
                "VALUES (?, 1, 1, 'Synthetic conversation', ?, 7, 0, ?, 0)",
                (conversation_id, conversation_id, bytes.fromhex(self.agent_id)),
            )
        self.before_others = self.other_rows()
        self.before_history = self.history_rows()

    def other_rows(self):
        with sqlite3.connect(self.database) as connection:
            return connection.execute("SELECT * FROM agents WHERE id != ? ORDER BY id",
                                      (bytes.fromhex(self.agent_id),)).fetchall()

    def history_rows(self):
        with sqlite3.connect(self.database) as connection:
            return connection.execute("SELECT * FROM conversations ORDER BY id").fetchall()

    def update(self, payload=b"new synthetic bundle", **kwargs):
        return update_existing(self.uri, self.artifacts, payload,
                               expected_version=kwargs.get("expected_version", 1),
                               expected_sha256=kwargs.get("expected_sha256", self.old_hash))

    def test_versioned_update_preserves_other_agents_history_and_old_artifact(self):
        result = self.update()
        self.assertEqual(result["version"], 2)
        self.assertEqual(result["agent_id"], self.agent_id)
        self.assertEqual(self.store.get_by_name("penny").bundle_location, result["bundle_location"])
        self.assertEqual(self.artifacts.get(self.old_location), self.old_payload)
        self.assertEqual(self.other_rows(), self.before_others)
        self.assertEqual(self.history_rows(), self.before_history)
        self.assertEqual(result["metadata"]["penny_bound_session_count"], 1)
        self.assertFalse(result["activation_verified"])
        self.assertTrue(result["live_cache_refresh_required"])
        self.assertFalse(result["model_execution_verified"])

    def test_repeating_current_content_does_not_bump_version(self):
        first = self.update()
        result = self.update(expected_version=2, expected_sha256=first["bundle_sha256"])
        self.assertEqual(result["version"], 2)
        self.assertEqual(result["action"], "already_current_activation_unverified")

    def test_stale_version_or_hash_does_not_change_template_or_artifacts(self):
        for kwargs in ({"expected_version": 2}, {"expected_sha256": "0" * 64}):
            with self.subTest(kwargs=kwargs), self.assertRaisesRegex(RuntimeError, "changed"):
                self.update(**kwargs)
        self.assertEqual(self.store.get_by_name("penny").version, 1)
        self.assertEqual(len(list((self.root / "artifacts" / self.agent_id).iterdir())), 1)

    def test_corrupt_old_artifact_refuses_update(self):
        self.artifacts.put(self.old_location, b"corrupted")
        with self.assertRaisesRegex(RuntimeError, "stored hash"):
            self.update()
        self.assertEqual(self.store.get_by_name("penny").version, 1)

    def test_write_failure_preserves_template(self):
        with patch.object(self.artifacts, "put", side_effect=OSError("synthetic disk failure")):
            with self.assertRaises(OSError):
                self.update()
        self.assertEqual(self.store.get_by_name("penny").version, 1)
        self.assertEqual(self.artifacts.get(self.old_location), self.old_payload)
        self.assertEqual(self.history_rows(), self.before_history)

    def test_conflicting_new_artifact_is_not_overwritten(self):
        digest = hashlib.sha256(b"new synthetic bundle").hexdigest()
        location = f"{self.agent_id}/{digest}"
        self.artifacts.put(location, b"different existing artifact")
        with self.assertRaisesRegex(RuntimeError, "occupied"):
            self.update()
        self.assertEqual(self.artifacts.get(location), b"different existing artifact")
        self.assertEqual(self.store.get_by_name("penny").version, 1)


class RuntimeGuardTests(unittest.TestCase):
    def test_active_runtime_and_schema_must_match_reviewed_adapter(self):
        with patch("importlib.metadata.version", return_value=VERIFIED_RUNTIME), \
                patch("scripts.manage.urlopen", return_value=io.BytesIO(json.dumps(
                    {"version": VERIFIED_RUNTIME}).encode())), \
                patch("scripts.manage.verify_existing_schema", return_value=VERIFIED_SCHEMA):
            self.assertEqual(verify_update_runtime("http://127.0.0.1:6767", "unused")["schema_revision"],
                             VERIFIED_SCHEMA)

    def test_obsolete_interpreter_is_rejected(self):
        with patch("importlib.metadata.version", return_value="0.12.0"), \
                patch("scripts.manage.urlopen", return_value=io.BytesIO(json.dumps(
                    {"version": VERIFIED_RUNTIME}).encode())):
            with self.assertRaisesRegex(RuntimeError, "interpreter"):
                verify_update_runtime("http://127.0.0.1:6767", "unused")

    def test_unreviewed_schema_is_rejected(self):
        with patch("importlib.metadata.version", return_value=VERIFIED_RUNTIME), \
                patch("scripts.manage.urlopen", return_value=io.BytesIO(json.dumps(
                    {"version": VERIFIED_RUNTIME}).encode())), \
                patch("scripts.manage.verify_existing_schema", return_value="unknown"):
            with self.assertRaisesRegex(RuntimeError, "schema"):
                verify_update_runtime("http://127.0.0.1:6767", "unused")


if __name__ == "__main__":
    unittest.main()
