"""Exercise approved model chains and evidence without invoking any provider."""

from dataclasses import asdict
from io import BytesIO
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import yaml

from scripts.manage import (
    BACKUP_MODEL, CHILDREN, EDITOR_MODEL, INLINE_START, MAX_CHILD_INSTRUCTION_BYTES, POWERFUL_MODEL, PROJECT, SKILL,
    build_bundle, exact_section, expected_fallbacks, expected_roles, fetch_claude_catalog, generation_plan,
    metadata_digest, tree_hashes, validate_bundle,
)


CATALOG = Path(__file__).parent / "fixtures/model_catalog.json"
CLAUDE_CATALOG = Path(__file__).parent / "fixtures/claude_model_catalog.json"


class GenerationTests(unittest.TestCase):
    def setUp(self):
        self.network = patch("scripts.manage.urlopen", side_effect=AssertionError("Unexpected network call"))
        self.network.start()
        self.addCleanup(self.network.stop)
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)
        self.bundle = self.directory / "bundle"

    def build(self, **kwargs):
        return build_bundle(self.bundle, model_catalog=CATALOG,
                            claude_model_catalog=CLAUDE_CATALOG, **kwargs)

    def plan(self, **kwargs):
        return generation_plan(CATALOG, claude_model_catalog=CLAUDE_CATALOG, **kwargs)

    def config_path(self, role):
        return ((self.bundle if role == "penny" else self.bundle / "agents" / role)
                / "config.yaml")

    def alter_config(self, role, change):
        path = self.config_path(role)
        config = yaml.safe_load(path.read_text())
        change(config)
        path.write_text(yaml.safe_dump(config))

    def alter_manifest(self, change):
        path = self.bundle / "generation.json"
        manifest = json.loads(path.read_text())
        change(manifest)
        path.write_text(json.dumps(manifest))

    def test_every_profile_preserves_exact_strong_dual_model_roles(self):
        for profile in ("message", "document", "learning"):
            with self.subTest(profile=profile):
                plan = self.plan(profile=profile)
                self.assertEqual(plan["profile"], profile)
                self.assertEqual(plan["roles"], {k: asdict(v) for k, v in expected_roles().items()})
                self.assertEqual(plan["role_fallbacks"], {
                    role: [asdict(candidate) for candidate in candidates]
                    for role, candidates in expected_fallbacks().items()})
                for role, primary in plan["roles"].items():
                    candidates = [primary, *plan["role_fallbacks"][role]]
                    self.assertEqual(len({row["model"] for row in candidates}), 3)
                    for priority, (candidate, evidence) in enumerate(zip(
                            candidates, plan["candidate_evidence"][role], strict=True)):
                        self.assertEqual({key: evidence[key] for key in candidate}, candidate)
                        self.assertEqual(evidence["priority"], priority)
                        self.assertIn(candidate["reasoning_effort"], evidence["runtime_supported_efforts"])
                        self.assertFalse(evidence["execution_verified"])
                self.assertFalse(plan["model_execution_verified"])
                self.assertFalse(plan["controls"]["live_enforcement_verified"])
                claude = plan["model_catalogs"]["claude-native"]
                self.assertFalse(claude["model_effort_metadata_available"])
                self.assertEqual(claude["effort_evidence"], "runtime_harness_only")
                self.assertIn("max", claude["runtime_supported_efforts"])

    def test_explicit_model_and_effort_downgrades_are_rejected(self):
        for kwargs in ({"model": "gpt-5.6-sol", "effort": "medium"}, {"effort": "high"}):
            with self.subTest(kwargs=kwargs), self.assertRaisesRegex(ValueError, "downgrades"):
                self.plan(**kwargs)

    def test_codex_runtime_rejects_ultra_and_max_even_when_catalog_advertises_them(self):
        for effort in ("ultra", "max"):
            with self.subTest(effort=effort), self.assertRaisesRegex(ValueError, "runtime harness"):
                self.plan(effort=effort)

    def test_unknown_model_effort_or_profile_never_falls_back(self):
        for kwargs in ({"model": "not-in-catalog"}, {"model": "gpt-5.6-sol", "effort": "ultra"},
                       {"effort": ""}, {"profile": "unbounded"}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                self.plan(**kwargs)

    def test_missing_claude_catalog_fails_without_a_network_request(self):
        with self.assertRaisesRegex(ValueError, "Claude model catalogue required"):
            generation_plan(CATALOG)
        with self.assertRaisesRegex(ValueError, "--host-id"):
            build_bundle(self.bundle, model_catalog=CATALOG)
        self.assertFalse(self.bundle.exists())

    def test_missing_codex_effort_refuses_build_before_creating_output(self):
        catalog = self.directory / "catalog.json"
        catalog.write_text(json.dumps({"models": [{"slug": POWERFUL_MODEL,
            "supported_reasoning_levels": [{"effort": "high"}]}]}))
        with self.assertRaisesRegex(ValueError, "unsupported"):
            build_bundle(self.bundle, model_catalog=catalog,
                         claude_model_catalog=CLAUDE_CATALOG, profile="message")
        self.assertFalse(self.bundle.exists())

    def test_missing_mismatched_or_ambiguous_fable_identity_is_rejected(self):
        for rows in ([], [{"id": "fable"}], [{"id": "fable", "model": "claude-fable-old"}],
                     [{"id": "opus", "model": EDITOR_MODEL}],
                     [{"id": "fable", "model": EDITOR_MODEL}] * 2):
            with self.subTest(rows=rows), self.assertRaisesRegex(ValueError, "Claude"):
                generation_plan(CATALOG, claude_model_catalog={"models": rows})

    def test_malformed_catalogues_are_rejected(self):
        for payload in ([], {}, {"models": "fable"}):
            with self.subTest(payload=payload), self.assertRaisesRegex(ValueError, "catalogue"):
                generation_plan(CATALOG, claude_model_catalog=payload)

    def test_missing_or_mismatched_backup_catalog_refuses_output(self):
        catalog = self.directory / "claude.json"
        for opus in (None, {"id": "opus", "model": "claude-opus-older"},
                     {"id": "other", "model": BACKUP_MODEL}):
            rows = [{"id": "fable", "model": EDITOR_MODEL}]
            if opus is not None:
                rows.append(opus)
            catalog.write_text(json.dumps({"models": rows}))
            with self.subTest(opus=opus), self.assertRaisesRegex(ValueError, "opus"):
                build_bundle(self.bundle, model_catalog=CATALOG, claude_model_catalog=catalog)
            self.assertFalse(self.bundle.exists())

    def test_backup_effort_requires_runtime_support(self):
        from omnigent.reasoning_effort import efforts_for_harness

        def supported(harness):
            return frozenset({"high"}) if harness == "claude-native" else efforts_for_harness(harness)

        with patch("omnigent.reasoning_effort.efforts_for_harness", side_effect=supported):
            with self.assertRaisesRegex(ValueError, "runtime harness"):
                self.build()
        self.assertFalse(self.bundle.exists())

    def test_claude_catalog_uses_exact_local_read_only_endpoint(self):
        payload = CLAUDE_CATALOG.read_bytes()
        with patch("scripts.manage.urlopen", return_value=BytesIO(payload)) as read:
            result = fetch_claude_catalog("http://127.0.0.1:6767", "test-host")
        read.assert_called_once_with(
            "http://127.0.0.1:6767/v1/hosts/test-host/harnesses/claude-native/model-options", timeout=10)
        self.assertEqual(result, json.loads(payload))

    def test_claude_catalog_never_uses_remote_or_ambiguous_host(self):
        for url in ("https://127.0.0.1:6767", "http://example.com", "http://localhost:6767/path",
                    "http://user@localhost:6767"):
            with self.subTest(url=url), self.assertRaisesRegex(ValueError, "local"):
                fetch_claude_catalog(url, "test-host")
        for host_id in (None, "", " "):
            with self.subTest(host_id=host_id), self.assertRaisesRegex(ValueError, "--host-id"):
                fetch_claude_catalog("http://127.0.0.1:6767", host_id)

    def test_build_fetches_claude_metadata_when_explicit_snapshot_not_supplied(self):
        with patch("scripts.manage.urlopen", return_value=BytesIO(CLAUDE_CATALOG.read_bytes())) as read:
            build_bundle(self.bundle, model_catalog=CATALOG, host_id="test-host")
        self.assertEqual(read.call_count, 1)
        self.assertTrue(validate_bundle(self.bundle)["valid"])

    def test_generated_configs_preserve_source_and_pass_native_effort_validation(self):
        from omnigent.runner.tool_dispatch import _validate_subagent_reasoning_effort
        from omnigent.server.routes._sessions.helpers import _derive_terminal_launch_args_from_spec
        from omnigent.spec import load

        original = tree_hashes(PROJECT / "omnigent")
        self.build(profile="message")
        self.assertTrue(validate_bundle(self.bundle)["valid"])
        for role, selection in expected_roles().items():
            root = self.config_path(role).parent
            spec = load(root, expand_env=False)
            self.assertEqual(_derive_terminal_launch_args_from_spec(spec),
                             ["--permission-mode", "manual"] if selection.harness == "claude-native" else None)
            self.assertEqual(spec.executor.harness_kind, selection.harness)
            self.assertEqual(_validate_subagent_reasoning_effort(
                spec.executor.reasoning_effort, spec.executor.harness_kind), selection.reasoning_effort)
            self.assertEqual([
                {"model": candidate.model, "reasoning_effort": candidate.reasoning_effort,
                 "harness": candidate.harness} for candidate in spec.executor.fallbacks
            ], [asdict(candidate) for candidate in expected_fallbacks()[role]])
        self.assertEqual(tree_hashes(PROJECT / "omnigent"), original)

    def test_archive_roundtrip_preserves_all_primary_and_fallback_candidates(self):
        from omnigent.server.app import _tar_gz_dir
        from omnigent.spec import load

        self.build()
        extracted = self.directory / "extracted"
        load(_tar_gz_dir(self.bundle), dest=extracted, expand_env=False)
        self.assertTrue(validate_bundle(extracted)["valid"])
        self.assertEqual(tree_hashes(self.bundle), tree_hashes(extracted))

    def test_validator_rejects_missing_reordered_or_replaced_backup(self):
        self.build()
        path = self.config_path("penny")
        original = path.read_text()
        changes = (
            lambda c: c["executor"].pop("fallbacks"),
            lambda c: c["executor"]["fallbacks"].reverse(),
            lambda c: c["executor"]["fallbacks"][1].update(model="claude-opus-other"),
        )
        for change in changes:
            with self.subTest(change=change):
                self.alter_config("penny", change)
                with self.assertRaisesRegex(ValueError, "approved ordered fallback"):
                    validate_bundle(self.bundle)
                path.write_text(original)

    def test_validator_rejects_changed_chain_even_when_manifest_matches(self):
        self.build()
        self.alter_config("reader", lambda c: c["executor"]["fallbacks"].reverse())
        self.alter_manifest(lambda m: m["role_fallbacks"]["reader"].reverse())
        with self.assertRaisesRegex(ValueError, "approved ordered fallback"):
            validate_bundle(self.bundle)

    def test_validator_rejects_missing_or_false_candidate_evidence(self):
        self.build()
        path = self.bundle / "generation.json"
        original = path.read_text()
        for change in (
            lambda m: m.pop("candidate_evidence"),
            lambda m: m["candidate_evidence"]["intent"].pop(),
            lambda m: m["candidate_evidence"]["reader"][1].update(execution_verified=True),
            lambda m: m["candidate_evidence"]["penny"][2].update(effort_evidence="model_verified"),
        ):
            with self.subTest(change=change):
                self.alter_manifest(change)
                with self.assertRaisesRegex(ValueError, "per-candidate"):
                    validate_bundle(self.bundle)
                path.write_text(original)

    def test_children_receive_exact_role_scoped_canonical_guidance(self):
        self.build()
        self.assertNotIn(INLINE_START, (self.bundle / "AGENTS.md").read_text())
        foundation = (SKILL / "SKILL.md").read_text().split("## Foundation\n", 1)[1].split(
            "## Understand the purpose before choosing the words\n", 1)[0]
        self.assertTrue(foundation.strip())
        sections = {
            "intent": ("## Establish the intent", "## Keep context current"),
            "reader": ("## Get the thought clear", "## Review the whole message"),
            "curator": ("# Learn the essence of writing the user likes",),
            "applier": ("## Draft in spoken language", "## Review the whole message"),
        }
        for role in CHILDREN:
            instructions = (self.config_path(role).parent / "AGENTS.md").read_text()
            self.assertEqual(instructions.count(INLINE_START), 1)
            self.assertIn("## Foundation\n" + foundation, instructions)
            for heading in sections[role]:
                self.assertIn("\n" + heading + "\n", instructions)
            self.assertNotIn((SKILL / "SKILL.md").read_text(), instructions)
            self.assertNotIn((SKILL / "references/cross-model-workflow.md").read_text(), instructions)
            self.assertLessEqual(len(instructions.encode("utf-8")), MAX_CHILD_INSTRUCTION_BYTES)
            self.assertEqual(tree_hashes(self.config_path(role).parent / "skills/penny"), tree_hashes(SKILL))
        self.assertIn((SKILL / "references/learning.md").read_text(),
                      (self.config_path("curator").parent / "AGENTS.md").read_text())
        manifest = json.loads((self.bundle / "generation.json").read_text())
        delivery = manifest["guidance_delivery"]["children"]
        self.assertEqual(delivery["mode"], "role_scoped_canonical_excerpts")
        self.assertFalse(delivery["full_shared_skill_loaded"])
        self.assertTrue(delivery["full_shared_skill_bundled"])

    def test_section_extraction_preserves_nested_text_and_stops_at_peer(self):
        content = "# Manual\n\n## First\n\nFirst text.\n### Detail\nKeep this.\n\n## Next\nExclude this.\n"
        self.assertEqual(exact_section(content, "## First", source="fixture.md"),
                         "## First\n\nFirst text.\n### Detail\nKeep this.\n\n")
        for content in ("## Different\nMissing.\n", "## First\nOne.\n## First\nTwo.\n"):
            with self.subTest(content=content), self.assertRaisesRegex(ValueError, "exactly once"):
                exact_section(content, "## First", source="fixture.md")

    def test_python_cache_is_not_a_source_input_or_allowed_bundle_artifact(self):
        source = self.directory / "source"
        source.mkdir()
        (source / "sample.py").write_text("pass\n")
        before = tree_hashes(source)
        cache = source / "__pycache__"
        cache.mkdir()
        (cache / "sample.cpython-test.pyc").write_bytes(b"local runtime cache")
        self.assertEqual(tree_hashes(source), before)
        self.build()
        self.assertFalse(any(p.name == "__pycache__" for p in self.bundle.rglob("*")))
        (self.bundle / "unexpected.pyc").write_bytes(b"cache")
        with self.assertRaisesRegex(ValueError, "bytecode caches"):
            validate_bundle(self.bundle)

    def test_oversized_utf8_child_instructions_fail_before_output_is_written(self):
        # Six thousand characters fit a character cap but exceed the UTF-8 cap
        # once combined with the child's role instructions.
        with patch("scripts.manage.inline_guidance", return_value="é" * 6000):
            with self.assertRaisesRegex(ValueError, "intent are [0-9]+ UTF-8 bytes; maximum 12000"):
                self.build()
        self.assertFalse(self.bundle.exists())

    def test_validator_rejects_false_claim_of_full_guidance_loaded(self):
        self.build()
        self.alter_manifest(lambda m: m["guidance_delivery"]["children"].update(full_shared_skill_loaded=True))
        with self.assertRaisesRegex(ValueError, "role-scoped canonical projection"):
            validate_bundle(self.bundle)

    def test_every_child_policy_denies_any_tool_call_but_allows_text_output(self):
        from omnigent.policies.function import make_fixed_action_callable

        self.build()
        for role in CHILDREN:
            config = yaml.safe_load(self.config_path(role).read_text())
            args = config["guardrails"]["policies"]["supplied_material_only"]["function"]["arguments"]
            policy = make_fixed_action_callable(**args)
            for target in ("shell", "read_skill_file", "write_file", "spawn_agent", "unknown"):
                with self.subTest(role=role, target=target):
                    self.assertEqual(policy({"type": "tool_call", "target": target})["result"], "deny")
            self.assertIsNone(policy({"type": "response", "target": None}))

    def test_validator_rejects_changed_role_even_when_manifest_matches(self):
        self.build()
        original_configs = {role: self.config_path(role).read_text() for role in expected_roles()}
        original_manifest = (self.bundle / "generation.json").read_text()
        for role in expected_roles():
            with self.subTest(role=role):
                self.alter_config(role, lambda c: c["executor"].update(reasoning_effort="high"))
                self.alter_manifest(lambda m: m["roles"][role].update(reasoning_effort="high"))
                with self.assertRaisesRegex(ValueError, "exact powerful"):
                    validate_bundle(self.bundle)
                self.config_path(role).write_text(original_configs[role])
                (self.bundle / "generation.json").write_text(original_manifest)

    def test_validator_rejects_codex_runtime_unsupported_effort(self):
        self.build()
        self.alter_config("penny", lambda c: c["executor"].update(reasoning_effort="ultra"))
        self.alter_manifest(lambda m: m["roles"]["penny"].update(reasoning_effort="ultra"))
        with self.assertRaisesRegex(ValueError, "runtime harness"):
            validate_bundle(self.bundle)

    def test_validator_rejects_native_permission_and_routing_bypasses(self):
        self.build()
        path = self.config_path("reader")
        original = path.read_text()
        for updates in ({"yolo": True}, {"yolo": "false"}, {"permission_mode": "bypassPermissions"},
                        {"smart_routing_harness": "codex-native"}, {"allowed_tools": ["shell"]}):
            with self.subTest(updates=updates):
                self.alter_config("reader", lambda c: c["executor"]["config"].update(updates))
                with self.assertRaisesRegex(ValueError, "bypass|routing"):
                    validate_bundle(self.bundle)
                path.write_text(original)

    def test_validator_rejects_missing_or_selectively_scoped_child_guardrail(self):
        self.build()
        for role in CHILDREN:
            path = self.config_path(role)
            original = path.read_text()
            changes = [lambda c: c.pop("guardrails"),
                       lambda c: c["guardrails"]["policies"]["supplied_material_only"].update(condition={"enabled": "yes"}),
                       lambda c: c["guardrails"]["policies"]["supplied_material_only"]["function"]["arguments"].update(on_tools=["shell"]),
                       lambda c: c["guardrails"]["policies"]["supplied_material_only"]["function"]["arguments"].update(action="allow")]
            for change in changes:
                with self.subTest(role=role, change=change):
                    self.alter_config(role, change)
                    with self.assertRaisesRegex(ValueError, "guardrail"):
                        validate_bundle(self.bundle)
                    path.write_text(original)

    def test_validator_rejects_inline_guidance_tampering(self):
        self.build()
        path = self.config_path("curator").parent / "AGENTS.md"
        path.write_text(path.read_text().replace(INLINE_START, "<!-- removed -->"))
        with self.assertRaisesRegex(ValueError, "inline guidance"):
            validate_bundle(self.bundle)

    def test_validator_rejects_child_tools_or_delegation(self):
        self.build()
        self.alter_config("reader", lambda c: c.update(tools={"builtins": ["web_search"]}))
        with self.assertRaisesRegex(ValueError, "Unexpected tools"):
            validate_bundle(self.bundle)

    def test_validator_rejects_undeclared_children(self):
        self.build()
        (self.bundle / "agents" / "writer").mkdir()
        with self.assertRaisesRegex(ValueError, "child directories"):
            validate_bundle(self.bundle)

    def test_validator_rejects_catalog_hash_or_model_identity_tampering(self):
        self.build()
        path = self.bundle / "generation.json"
        original = path.read_text()
        for harness in ("codex-native", "claude-native"):
            with self.subTest(harness=harness):
                self.alter_manifest(lambda m: m["model_catalogs"][harness].update(metadata_sha256="0" * 64))
                with self.assertRaisesRegex(ValueError, "catalogue evidence"):
                    validate_bundle(self.bundle)
                path.write_text(original)
        def wrong_claude(manifest):
            evidence = {"fable": "claude-fable-old"}
            manifest["model_catalogs"]["claude-native"].update(
                model_aliases=evidence, metadata_sha256=metadata_digest(evidence))
        self.alter_manifest(wrong_claude)
        with self.assertRaisesRegex(ValueError, "Claude"):
            validate_bundle(self.bundle)

    def test_validator_rejects_unearned_execution_or_effort_claims(self):
        self.build()
        path = self.bundle / "generation.json"
        original = path.read_text()
        for change in (lambda m: m.update(model_execution_verified=True),
                       lambda m: m["controls"].update(live_enforcement_verified=True),
                       lambda m: m["model_catalogs"]["claude-native"].update(model_effort_metadata_available=True)):
            self.alter_manifest(change)
            with self.assertRaises(ValueError):
                validate_bundle(self.bundle)
            path.write_text(original)

    def test_build_is_idempotent_and_does_not_overwrite_different_output(self):
        self.build()
        original = tree_hashes(self.bundle)
        self.build()
        self.assertEqual(tree_hashes(self.bundle), original)
        path = self.bundle / "AGENTS.md"
        path.write_text("User work that must be preserved.\n")
        with self.assertRaises(FileExistsError):
            self.build()
        self.assertEqual(path.read_text(), "User work that must be preserved.\n")


if __name__ == "__main__":
    unittest.main()
