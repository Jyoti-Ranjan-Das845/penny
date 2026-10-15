#!/usr/bin/env python3
"""Install Penny, generate a validated bundle, or version its local template."""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from enum import StrEnum
import hashlib
import json
from pathlib import Path
import re
import shutil
import sqlite3
import tempfile
import time
from urllib.parse import quote, urlencode, urlsplit
from urllib.request import urlopen


PROJECT = Path(__file__).resolve().parents[1]
SKILL = PROJECT / "skills" / "penny"
NAME = "penny"
CHILDREN = ("intent", "curator", "reader", "applier")
POWERFUL_MODEL = "gpt-6-astra"
POWERFUL_EFFORT = "xhigh"
EDITOR_MODEL = "claude-fable-5-1"
EDITOR_EFFORT = "max"
EDITOR_ALIAS = "fable"
BACKUP_MODEL = "claude-opus-5"
BACKUP_ALIAS = "opus"
BACKUP_EFFORT = "max"
VERIFIED_RUNTIME = "0.13.0.dev0"
VERIFIED_SCHEMA = "gb1b2c3d4e5f"
INLINE_START = "<!-- BEGIN PENNY TRUSTED INLINE GUIDANCE -->"
INLINE_END = "<!-- END PENNY TRUSTED INLINE GUIDANCE -->"
MAX_CHILD_INSTRUCTION_BYTES = 12000
DENY_TOOL_REASON = "This role reviews only the supplied material; tool calls are disabled."


class BuildProfile(StrEnum):
    MESSAGE = "message"
    DOCUMENT = "document"
    LEARNING = "learning"


@dataclass(frozen=True)
class ModelSelection:
    model: str
    reasoning_effort: str
    harness: str = "codex-native"


def expected_roles() -> dict[str, ModelSelection]:
    """Profiles change workflow, never the configured quality of any role."""
    astra = ModelSelection(POWERFUL_MODEL, POWERFUL_EFFORT)
    fable = ModelSelection(EDITOR_MODEL, EDITOR_EFFORT, "claude-native")
    return {NAME: astra, "intent": astra, "curator": fable, "reader": fable, "applier": astra}


def expected_fallbacks() -> dict[str, tuple[ModelSelection, ModelSelection]]:
    """The approved ordered chains are fixed, not inferred from model names."""
    astra = ModelSelection(POWERFUL_MODEL, POWERFUL_EFFORT)
    fable = ModelSelection(EDITOR_MODEL, EDITOR_EFFORT, "claude-native")
    opus = ModelSelection(BACKUP_MODEL, BACKUP_EFFORT, "claude-native")
    return {role: (fable, opus) if primary == astra else (opus, astra)
            for role, primary in expected_roles().items()}


def candidate_evidence() -> dict[str, list[dict]]:
    """Record the exact source and limits of each configured candidate's evidence."""
    evidence = {}
    for role, primary in expected_roles().items():
        candidates = (primary, *expected_fallbacks()[role])
        evidence[role] = [{
            **asdict(candidate),
            "priority": index,
            "model_identity_evidence": "host_model_catalog" if candidate.harness == "codex-native"
                else "claude_native_model_options",
            "catalog_alias": ({EDITOR_MODEL: EDITOR_ALIAS, BACKUP_MODEL: BACKUP_ALIAS}
                              .get(candidate.model)),
            "effort_evidence": "host_model_catalog_and_runtime_harness"
                if candidate.harness == "codex-native" else "runtime_harness_only",
            "runtime_supported_efforts": sorted(validate_runtime_effort(candidate, role)),
            "execution_verified": False,
        } for index, candidate in enumerate(candidates)]
    return evidence


def child_guardrails() -> dict:
    return {"policies": {"supplied_material_only": {
        "type": "function",
        "function": {
            "path": "omnigent.policies.function.make_fixed_action_callable",
            "arguments": {"action": "deny", "on_phases": ["tool_call"],
                          "reason": DENY_TOOL_REASON},
        },
    }}}


def configured_controls() -> dict:
    """Describe configured controls without claiming provider execution proof."""
    return {
        "enforced_configuration": {
            "native_yolo": False,
            "claude_permission_mode": "manual",
            "children_tool_calls": "deny_all_via_function_policy",
            "role_models": "exact_ordered_primary_and_two_fallbacks",
        },
        "instruction_only": ["evidence_preservation", "independent_reader_review",
                             "quality_gate", "authorized_learning", "shared_log_preload"],
        "live_enforcement_verified": False,
    }


def metadata_digest(evidence: dict) -> str:
    return hashlib.sha256(json.dumps(evidence, sort_keys=True).encode()).hexdigest()


def guidance_delivery() -> dict:
    foundation = {"path": "SKILL.md", "heading": "## Foundation"}
    return {
        "root": "bundled_skill_loaded_on_demand",
        "children": {
            "mode": "role_scoped_canonical_excerpts",
            "full_shared_skill_bundled": True,
            "full_shared_skill_loaded": False,
            "additional_guidance": "lead_supplied_in_task_message",
            "max_instruction_utf8_bytes": MAX_CHILD_INSTRUCTION_BYTES,
            "projections": {
                "intent": [foundation,
                           {"path": "references/document-workflow.md", "heading": "## Establish the intent"},
                           {"path": "references/document-workflow.md", "heading": "## Keep context current"}],
                "reader": [foundation,
                           {"path": "SKILL.md", "heading": "## Get the thought clear"},
                           {"path": "SKILL.md", "heading": "## Review the whole message"}],
                "curator": [foundation, {"path": "references/learning.md", "heading": None}],
                "applier": [foundation,
                            {"path": "SKILL.md", "heading": "## Draft in spoken language"},
                            {"path": "SKILL.md", "heading": "## Review the whole message"}],
            },
        },
    }


def exact_section(content: str, heading: str, *, source: str) -> str:
    """Return one exact ATX heading section, preserving its original text."""
    match = re.fullmatch(r"(#{1,6}) .+", heading)
    if not match:
        raise ValueError(f"Expected an exact Markdown heading, got {heading!r}")
    lines = content.splitlines(keepends=True)
    starts = [index for index, line in enumerate(lines) if line.rstrip("\r\n") == heading]
    if len(starts) != 1:
        raise ValueError(f"Canonical section {heading!r} in {source} must occur exactly once; "
                         f"found {len(starts)}")
    start = starts[0]
    depth = len(match[1])
    end = len(lines)
    for index in range(start + 1, len(lines)):
        next_heading = re.match(r"^(#{1,6}) .+", lines[index])
        if next_heading and len(next_heading[1]) <= depth:
            end = index
            break
    return "".join(lines[start:end])


def inline_guidance(role: str) -> str:
    parts = [INLINE_START,
             "These are trusted, role-scoped canonical excerpts from the full shared Penny guidance. "
             "The full identical skill remains bundled; only the excerpts below are loaded inline. "
             "The lead owns cross-model coordination and source retrieval. "
             "As a child, perform only your assigned phase and return its text result; "
             "do not coordinate additional models. The lead supplies additional relevant guidance "
             "in the task message when needed. References below do not grant permission to read "
             "files or call tools; apply the supplied material and report any missing context to the lead."]
    for entry in guidance_delivery()["children"]["projections"][role]:
        relative, heading = entry["path"], entry["heading"]
        content = (SKILL / relative).read_text()
        if heading is not None:
            content = exact_section(content, heading, source=relative)
        label = relative if heading is None else f"{relative}: {heading}"
        parts.extend([f"<!-- BEGIN CANONICAL {label} -->", content,
                      f"<!-- END CANONICAL {label} -->"])
    parts.append(INLINE_END)
    return "\n\n".join(parts) + "\n"


def agent_instructions(role: str) -> str:
    source = PROJECT / "omnigent"
    if role != NAME:
        source = source / "agents" / role
    instructions = (source / "AGENTS.md").read_text()
    if INLINE_START in instructions or INLINE_END in instructions:
        raise ValueError("Source instructions must not contain generated inline guidance")
    if role == NAME:
        return instructions
    compiled = instructions.rstrip() + "\n\n" + inline_guidance(role)
    size = len(compiled.encode("utf-8"))
    if size > MAX_CHILD_INSTRUCTION_BYTES:
        raise ValueError(f"Compiled instructions for {role} are {size} UTF-8 bytes; "
                         f"maximum {MAX_CHILD_INSTRUCTION_BYTES}. Review the role instructions "
                         "or canonical projection; no content was truncated and no bundle was written")
    return compiled


def validate_runtime_effort(selection: ModelSelection, role: str) -> frozenset[str]:
    """Require the exact runtime effort, never an alias or a default fallback."""
    from omnigent.reasoning_effort import efforts_for_harness

    supported = efforts_for_harness(selection.harness)
    if not supported or selection.reasoning_effort not in supported:
        raise ValueError(
            f"Effort {selection.reasoning_effort!r} for {role} is unsupported by "
            f"the runtime harness {selection.harness!r}; no fallback was selected"
        )
    return supported


def generation_plan(
    model_catalog: Path,
    *,
    claude_model_catalog: Path | dict | None = None,
    profile: str = BuildProfile.DOCUMENT,
    model: str = POWERFUL_MODEL,
    effort: str | None = None,
) -> dict:
    """Require both explicit model identities and adapter-supported effort."""
    selected_profile = BuildProfile(profile)
    raw = json.loads(model_catalog.read_text())
    if not isinstance(raw, dict) or not isinstance(raw.get("models"), list):
        raise ValueError("Expected a Codex model catalogue with a models list")
    supported = {}
    for row in raw["models"]:
        if not isinstance(row, dict) or not isinstance(row.get("slug"), str):
            continue
        levels = row.get("supported_reasoning_levels", [])
        if isinstance(levels, list):
            supported[row["slug"]] = {
                item["effort"] for item in levels
                if isinstance(item, dict) and isinstance(item.get("effort"), str)
            }
    # Keep the old options for actionable failures, not as downgrade switches.
    requested = ModelSelection(model, effort if effort is not None else POWERFUL_EFFORT)
    if requested.model not in supported:
        raise ValueError(f"Model {requested.model!r} is absent from the Codex host catalogue")
    if requested.reasoning_effort not in supported[requested.model]:
        raise ValueError(f"Effort {requested.reasoning_effort!r} is unsupported by "
                         f"{requested.model!r}; no fallback was selected")
    validate_runtime_effort(requested, NAME)
    if requested != expected_roles()[NAME]:
        raise ValueError("Penny requires gpt-6-astra at xhigh; model/effort downgrades are disabled")
    if claude_model_catalog is None:
        raise ValueError("Claude model catalogue required; supply --claude-model-catalog or --host-id")
    claude_raw = (json.loads(claude_model_catalog.read_text())
                  if isinstance(claude_model_catalog, Path) else claude_model_catalog)
    if not isinstance(claude_raw, dict) or not isinstance(claude_raw.get("models"), list):
        raise ValueError("Expected a Claude native model-options catalogue with a models list")
    aliases = {}
    for row in claude_raw["models"]:
        if not isinstance(row, dict) or not isinstance(row.get("id"), str):
            continue
        if row["id"] in aliases:
            raise ValueError(f"Duplicate Claude catalogue model alias: {row['id']!r}")
        aliases[row["id"]] = row.get("model")
    for alias, expected in ((EDITOR_ALIAS, EDITOR_MODEL), (BACKUP_ALIAS, BACKUP_MODEL)):
        if aliases.get(alias) != expected:
            raise ValueError(f"Claude catalogue must resolve {alias!r} to {expected!r}; "
                             "missing or mismatched model; bundle was not generated")
    roles = expected_roles()
    for role, primary in roles.items():
        for selection in (primary, *expected_fallbacks()[role]):
            if (selection.harness == "codex-native"
                    and selection.reasoning_effort not in supported.get(selection.model, set())):
                raise ValueError(
                    f"Effort {selection.reasoning_effort!r} for {role} is unsupported by "
                    f"{selection.model!r}; bundle was not generated"
                )
            validate_runtime_effort(selection, role)
    codex_evidence = {POWERFUL_MODEL: sorted(supported[POWERFUL_MODEL])}
    claude_evidence = {EDITOR_ALIAS: EDITOR_MODEL, BACKUP_ALIAS: BACKUP_MODEL}
    catalogs = {
        "codex-native": {
            "source": "host_model_catalog",
            "supported_efforts": codex_evidence,
            "metadata_sha256": metadata_digest(codex_evidence),
        },
        "claude-native": {
            "source": "claude_native_model_options",
            "model_aliases": claude_evidence,
            "metadata_sha256": metadata_digest(claude_evidence),
            "model_effort_metadata_available": False,
            "effort_evidence": "runtime_harness_only",
            "runtime_supported_efforts": sorted(validate_runtime_effort(roles["reader"], "reader")),
        },
    }
    return {
        "profile": selected_profile.value,
        "roles": {role: asdict(selection) for role, selection in roles.items()},
        "role_fallbacks": {role: [asdict(selection) for selection in fallbacks]
                           for role, fallbacks in expected_fallbacks().items()},
        "candidate_evidence": candidate_evidence(),
        "model_catalogs": catalogs,
        "configuration_status": "ordered_fallbacks_configured_execution_unverified",
        "guidance_delivery": guidance_delivery(),
        "controls": configured_controls(),
        "model_execution_verified": False,
    }


def tree_hashes(root: Path) -> dict[str, str]:
    return {
        str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(root.rglob("*"))
        if path.is_file() and "__pycache__" not in path.parts and path.suffix not in {".pyc", ".pyo"}
    }


def install_skills(home: Path) -> dict:
    """Expose one source to Codex's shared discovery path and Claude's path."""
    targets = [home / ".agents/skills/penny", home / ".claude/skills/penny"]
    for target in targets:
        if target.is_symlink() and target.resolve() == SKILL:
            continue
        if target.exists() or target.is_symlink():
            raise FileExistsError(f"Existing skill at {target}; no replacement performed")
    for target in targets:
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.is_symlink():
            target.symlink_to(SKILL, target_is_directory=True)
    return {"source": str(SKILL), "installed": [str(p) for p in targets]}


def build_bundle(
    output: Path,
    *,
    profile: str = BuildProfile.DOCUMENT,
    model: str = POWERFUL_MODEL,
    effort: str | None = None,
    model_catalog: Path | None = None,
    claude_model_catalog: Path | None = None,
    host_id: str | None = None,
    api_url: str = "http://127.0.0.1:6767",
) -> dict:
    """Generate a fresh bundle without changing the portable source or prior builds."""
    import yaml

    if output.is_symlink():
        raise ValueError("Bundle output must be a directory, not a symlink")
    if claude_model_catalog is None:
        claude_catalog = fetch_claude_catalog(api_url, host_id)
    else:
        claude_catalog = claude_model_catalog
    plan = generation_plan(
        model_catalog or Path.home() / ".codex/models_cache.json",
        claude_model_catalog=claude_catalog, profile=profile, model=model, effort=effort,
    )
    with tempfile.TemporaryDirectory(prefix="penny-build-") as directory:
        root = Path(directory) / NAME
        shutil.copytree(PROJECT / "omnigent", root)
        for name in (NAME, *CHILDREN):
            agent_root = root if name == NAME else root / "agents" / name
            config_path = agent_root / "config.yaml"
            config = yaml.safe_load(config_path.read_text())
            if not isinstance(config, dict) or config.get("name") != name:
                raise ValueError(f"Unexpected source agent identity: {config_path}")
            executor = config.setdefault("executor", {})
            executor["type"] = "omnigent"
            selection = plan["roles"][name]
            executor["model"] = selection["model"]
            executor["reasoning_effort"] = selection["reasoning_effort"]
            executor["fallbacks"] = plan["role_fallbacks"][name]
            settings = executor.setdefault("config", {})
            settings["harness"] = selection["harness"]
            settings["yolo"] = False
            settings.pop("smart_routing_harness", None)
            if selection["harness"] == "claude-native":
                settings["permission_mode"] = "manual"
            config_path.write_text(yaml.safe_dump(config, sort_keys=False, allow_unicode=True))
            (agent_root / "AGENTS.md").write_text(agent_instructions(name))
            shutil.copytree(SKILL, agent_root / "skills/penny",
                            ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo"))
        (root / "generation.json").write_text(json.dumps(plan, indent=2, sort_keys=True) + "\n")
        validate_bundle(root)
        expected = tree_hashes(root)
        if output.exists():
            if not output.is_dir() or tree_hashes(output) != expected:
                raise FileExistsError(f"Different content at {output}; use a new output path")
        else:
            output.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(root, output)
    return {"bundle": str(output), "files": len(expected),
            "skill_sha256": expected["skills/penny/SKILL.md"], "generation": plan}


def validate_bundle(root: Path) -> dict:
    import yaml
    from omnigent.spec import load

    if any(p.name == "__pycache__" or p.suffix in {".pyc", ".pyo"} for p in root.rglob("*")):
        raise ValueError("Generated bundles must not include Python bytecode caches")

    manifest = json.loads((root / "generation.json").read_text())
    BuildProfile(manifest["profile"])
    if set(manifest["roles"]) != {NAME, *CHILDREN}:
        raise ValueError("Generation manifest has unexpected roles")
    if manifest.get("model_execution_verified") is not False:
        raise ValueError("A generated bundle cannot claim model execution verified")
    if manifest.get("configuration_status") != "ordered_fallbacks_configured_execution_unverified":
        raise ValueError("Missing ordered-fallback configuration status")
    approved_fallbacks = {role: [asdict(selection) for selection in fallbacks]
                          for role, fallbacks in expected_fallbacks().items()}
    if manifest.get("role_fallbacks") != approved_fallbacks:
        raise ValueError("Each role requires its exact approved ordered fallback chain")
    if manifest.get("candidate_evidence") != candidate_evidence():
        raise ValueError("Missing or invalid per-candidate model/harness/effort evidence")
    if manifest.get("controls") != configured_controls():
        raise ValueError("Control evidence differs from the configured, unverified controls")
    if manifest.get("guidance_delivery") != guidance_delivery():
        raise ValueError("Guidance delivery must record the exact role-scoped canonical projection")
    catalogs = manifest.get("model_catalogs", {})
    if set(catalogs) != {"codex-native", "claude-native"}:
        raise ValueError("Both Codex and Claude catalogue evidence are required")
    codex = catalogs["codex-native"]
    codex_evidence = codex.get("supported_efforts", {})
    if (codex.get("source") != "host_model_catalog"
            or set(codex_evidence) != {POWERFUL_MODEL}
            or POWERFUL_EFFORT not in codex_evidence[POWERFUL_MODEL]
            or codex.get("metadata_sha256") != metadata_digest(codex_evidence)):
        raise ValueError("Invalid Codex supported model/effort catalogue evidence")
    claude = catalogs["claude-native"]
    claude_evidence = claude.get("model_aliases", {})
    if (claude.get("source") != "claude_native_model_options"
            or claude_evidence != {EDITOR_ALIAS: EDITOR_MODEL, BACKUP_ALIAS: BACKUP_MODEL}
            or claude.get("metadata_sha256") != metadata_digest(claude_evidence)
            or claude.get("model_effort_metadata_available") is not False
            or claude.get("effort_evidence") != "runtime_harness_only"
            or claude.get("runtime_supported_efforts")
            != sorted(validate_runtime_effort(expected_roles()["reader"], "reader"))):
        raise ValueError("Invalid Claude model/adapter-effort catalogue evidence")
    agent_directories = root / "agents"
    if not agent_directories.is_dir() or {p.name for p in agent_directories.iterdir()} != set(CHILDREN):
        raise ValueError(f"Expected exactly {', '.join(CHILDREN)} child directories")
    for name in (NAME, *CHILDREN):
        relative = Path(".") if name == NAME else Path("agents") / name
        agent_root = root / relative
        config = yaml.safe_load((agent_root / "config.yaml").read_text())
        spec = load(agent_root, expand_env=False)
        if spec.name != name or not spec.description:
            raise ValueError(f"Missing identity or description: {relative}")
        if spec.skills_filter != "none" or [s.name for s in spec.skills] != [NAME]:
            raise ValueError(f"Unexpected skill discovery: {relative}")
        if tree_hashes(root / relative / "skills/penny") != tree_hashes(SKILL):
            raise ValueError("Bundled writing guidance differs from the common skill")
        selection = manifest["roles"][name]
        actual = ModelSelection(spec.executor.model, spec.executor.reasoning_effort,
                                spec.executor.harness_kind)
        if asdict(actual) != selection:
            raise ValueError(f"Generated executor differs from the manifest: {name}")
        validate_runtime_effort(actual, name)
        if actual != expected_roles()[name]:
            raise ValueError(f"Role requires its exact powerful configured model and effort: {name}")
        if not hasattr(spec.executor, "fallbacks"):
            raise ValueError("Runtime does not support typed executor.fallbacks; upgrade before building")
        actual_fallbacks = [asdict(ModelSelection(item.model, item.reasoning_effort, item.harness))
                            for item in spec.executor.fallbacks]
        if actual_fallbacks != approved_fallbacks[name]:
            raise ValueError(f"Role requires its exact approved ordered fallback chain: {name}")
        for item in spec.executor.fallbacks:
            validate_runtime_effort(ModelSelection(item.model, item.reasoning_effort, item.harness), name)
        if config["executor"].get("config", {}).get("yolo") is not False:
            raise ValueError(f"Native approval bypass must be explicitly disabled: {name}")
        if "smart_routing_harness" in spec.executor.config:
            raise ValueError(f"Automatic routing would override the generated executor: {name}")
        settings = {"harness": actual.harness, "yolo": False}
        if actual.harness == "claude-native":
            settings["permission_mode"] = "manual"
        expected_executor = {"type": "omnigent", "model": actual.model,
                             "reasoning_effort": actual.reasoning_effort, "config": settings,
                             "fallbacks": approved_fallbacks[name]}
        if config.get("executor") != expected_executor:
            raise ValueError(f"Unexpected executor settings or permission/routing bypass: {name}")
        if config.get("instructions") != "AGENTS.md" or (agent_root / "AGENTS.md").read_text() != agent_instructions(name):
            raise ValueError(f"Agent instructions or canonical inline guidance differ: {name}")
        if config.get("tools", {}) != ({"agents": list(CHILDREN)} if name == NAME else {}):
            raise ValueError(f"Unexpected tools or child delegation: {name}")
        if spec.tools.builtins or spec.local_tools or spec.mcp_servers:
            raise ValueError(f"Unexpected builtin, local, or MCP tools: {name}")
        if name in CHILDREN:
            if config.get("guardrails") != child_guardrails():
                raise ValueError(f"Child must deny every tool call with the exact guardrail: {name}")
            if (agent_root / "agents").exists() or spec.tools.agents:
                raise ValueError(f"Unexpected nested child agents: {name}")
    parent = load(root, expand_env=False)
    if set(parent.tools.agents) != set(CHILDREN):
        raise ValueError(f"Expected exactly {', '.join(CHILDREN)} children")
    return {"valid": True, "root": NAME, "children": list(CHILDREN),
            "description": parent.description, "generation": manifest}


def local_api_url(api_url: str) -> str:
    parsed = urlsplit(api_url)
    if (parsed.scheme != "http" or parsed.hostname not in {"localhost", "127.0.0.1"}
            or parsed.username or parsed.password or parsed.query or parsed.fragment
            or parsed.path not in {"", "/"}):
        raise ValueError("Use the local Omnigent server URL")
    return api_url.rstrip("/")


def fetch_claude_catalog(api_url: str, host_id: str | None) -> dict:
    """Read model options only; this never starts or changes a session."""
    base = local_api_url(api_url)
    if not host_id or not host_id.strip():
        raise ValueError("Supply --host-id for the local Claude catalogue, or --claude-model-catalog "
                         "for an explicit saved snapshot; host identity is not guessed")
    endpoint = f"{base}/v1/hosts/{quote(host_id, safe='')}/harnesses/claude-native/model-options"
    with urlopen(endpoint, timeout=10) as response:
        payload = json.load(response)
    if not isinstance(payload, dict):
        raise ValueError("Malformed Claude model-options catalogue")
    return payload


def catalogue(api_url: str) -> dict[str, dict]:
    api_url = local_api_url(api_url)
    rows = {}
    after = None
    while True:
        query = {"limit": 1000}
        if after:
            query["after"] = after
        with urlopen(api_url.rstrip("/") + "/v1/agents?" + urlencode(query), timeout=10) as response:
            page = json.load(response)
        for row in page["data"]:
            rows[row["id"]] = {key: row.get(key) for key in (
                "id", "name", "version", "description", "harness", "builtin", "skills"
            )}
        if not page.get("has_more"):
            return rows
        next_cursor = page.get("last_id") or page["data"][-1]["id"]
        if next_cursor == after:
            raise RuntimeError("Catalogue pagination did not advance")
        after = next_cursor


def verify_existing_schema(database_uri: str) -> str:
    from sqlalchemy import create_engine
    from omnigent.db.utils import _get_current_db_revision, _get_head_db_revision

    if not database_uri.startswith("sqlite:////"):
        raise ValueError("Use an absolute SQLite URI for the existing local server")
    database = Path(database_uri.removeprefix("sqlite:///"))
    if not database.is_file() or database.is_symlink():
        raise ValueError("Expected the existing server database")
    engine = create_engine(database_uri)
    try:
        current = _get_current_db_revision(engine)
        if current != _get_head_db_revision(database_uri):
            raise RuntimeError("Schema mismatch; this installer does not run live migrations")
        return current
    finally:
        engine.dispose()


def verify_update_runtime(api_url: str, database_uri: str) -> dict:
    """Refuse schema drift or a CLI interpreter unlike the running server."""
    from importlib.metadata import version
    import omnigent.spec

    interpreter_version = version("omnigent")
    with urlopen(local_api_url(api_url) + "/api/version", timeout=10) as response:
        server_version = json.load(response).get("version")
    if interpreter_version != VERIFIED_RUNTIME or server_version != VERIFIED_RUNTIME:
        raise RuntimeError(
            f"Update adapter requires running server and interpreter {VERIFIED_RUNTIME}; "
            f"found server={server_version!r}, interpreter={interpreter_version!r}"
        )
    revision = verify_existing_schema(database_uri)
    if revision != VERIFIED_SCHEMA:
        raise RuntimeError("Update adapter has not been reviewed for this database schema")
    return {"server_version": server_version, "interpreter_version": interpreter_version,
            "runtime_module": str(Path(omnigent.spec.__file__).resolve()), "schema_revision": revision}


def database_path(database_uri: str) -> Path:
    if not database_uri.startswith("sqlite:////"):
        raise ValueError("Use an absolute SQLite URI for the existing local server")
    database = Path(database_uri.removeprefix("sqlite:///"))
    if not database.is_file() or database.is_symlink():
        raise ValueError("Expected the existing server database")
    return database


def _metadata_snapshot(connection: sqlite3.Connection, penny_id: bytes) -> dict:
    others = connection.execute(
        "SELECT workspace_id, lower(hex(id)), name, version, bundle_location, updated_at, kind "
        "FROM agents WHERE NOT (workspace_id = 0 AND id = ?) ORDER BY workspace_id, id", (penny_id,),
    ).fetchall()
    history = connection.execute(
        "SELECT workspace_id, lower(hex(id)), lower(hex(agent_id)), next_position "
        "FROM conversations ORDER BY workspace_id, id"
    ).fetchall()
    bound = connection.execute(
        "SELECT count(*) FROM conversations WHERE workspace_id = 0 AND agent_id = ?", (penny_id,),
    ).fetchone()[0]
    return {
        "other_agents_sha256": hashlib.sha256(json.dumps(others).encode()).hexdigest(),
        "conversation_bindings_sha256": hashlib.sha256(json.dumps(history).encode()).hexdigest(),
        "conversation_count": len(history), "penny_bound_session_count": bound,
    }


def update_existing(
    database_uri: str,
    artifacts,
    payload: bytes,
    *,
    expected_version: int,
    expected_sha256: str,
) -> dict:
    """Atomically change only Penny's template pointer; leave live caches untouched."""
    from omnigent.db.utils import builtin_agent_id

    if expected_version < 1 or len(expected_sha256) != 64:
        raise ValueError("Supply a positive expected version and full previous SHA-256")
    try:
        if len(bytes.fromhex(expected_sha256)) != 32:
            raise ValueError("Expected SHA-256 must contain 32 bytes")
    except ValueError as exc:
        raise ValueError("Expected SHA-256 must be hexadecimal") from exc
    expected_sha256 = expected_sha256.lower()
    digest = hashlib.sha256(payload).hexdigest()
    agent_id = builtin_agent_id(NAME)
    binary_id = bytes.fromhex(agent_id)
    connection = sqlite3.connect(database_path(database_uri), timeout=10)
    try:
        connection.execute("BEGIN IMMEDIATE")
        row = connection.execute(
            "SELECT name, version, bundle_location, kind FROM agents "
            "WHERE workspace_id = 0 AND id = ?", (binary_id,),
        ).fetchone()
        if row is None or row[0] != NAME or row[3] != 1:
            raise RuntimeError("Expected Penny's existing deterministic template; nothing was changed")
        _, current_version, old_location, _ = row
        current_digest = old_location.rsplit("/", 1)[-1]
        if current_version != expected_version or current_digest != expected_sha256:
            raise RuntimeError("Penny changed since preflight; expected version/hash do not match")
        if not artifacts.exists(old_location):
            raise RuntimeError("Previous Penny artifact is missing; refusing update")
        if hashlib.sha256(artifacts.get(old_location)).hexdigest() != current_digest:
            raise RuntimeError("Previous Penny artifact does not match its stored hash")
        before = _metadata_snapshot(connection, binary_id)
        new_location = f"{agent_id}/{digest}"
        action = "already_current_activation_unverified"
        if digest != current_digest:
            if artifacts.exists(new_location):
                if artifacts.get(new_location) != payload:
                    raise RuntimeError("New artifact key is occupied by different content")
            else:
                artifacts.put(new_location, payload)
            if hashlib.sha256(artifacts.get(new_location)).hexdigest() != digest:
                raise RuntimeError("New Penny artifact failed read-back verification")
            changed = connection.execute(
                "UPDATE agents SET bundle_location = ?, version = version + 1, updated_at = ? "
                "WHERE workspace_id = 0 AND id = ? AND name = ? AND kind = 1 "
                "AND version = ? AND bundle_location = ?",
                (new_location, int(time.time()), binary_id, NAME, expected_version, old_location),
            )
            if changed.rowcount != 1:
                raise RuntimeError("Penny compare-and-swap failed; template update rolled back")
            action = "template_updated_activation_pending"
        after = _metadata_snapshot(connection, binary_id)
        if after != before:
            raise RuntimeError("Unrelated metadata changed; template update rolled back")
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()
    return {
        "action": action, "agent_id": agent_id,
        "previous_version": current_version,
        "version": current_version + (digest != current_digest),
        "previous_bundle_location": old_location,
        "previous_bundle_sha256": current_digest,
        "bundle_location": new_location if digest != current_digest else old_location,
        "bundle_sha256": digest,
        "previous_artifact_preserved": True,
        "other_agents_unchanged": True,
        "conversation_records_unchanged": True,
        "metadata": after,
        "activation_verified": False,
        "live_cache_refresh_required": True,
        "model_execution_verified": False,
        "existing_session_behavior": "History remains; resumed sessions may use the updated template.",
    }


def update(args) -> dict:
    from omnigent.server.app import _tar_gz_dir
    from omnigent.stores.agent_store.sqlalchemy_store import SqlAlchemyAgentStore
    from omnigent.stores.artifact_store.local import LocalArtifactStore

    if args.report.exists() or args.report.is_symlink():
        raise FileExistsError("Choose a fresh report path to preserve prior evidence")
    validation = validate_bundle(args.bundle)
    runtime = verify_update_runtime(args.api_url, args.database_uri)
    if (not args.artifact_location.is_absolute() or not args.artifact_location.is_dir()
            or args.artifact_location.is_symlink()):
        raise ValueError("Use the existing server's absolute artifact directory")
    before = catalogue(args.api_url)
    store = SqlAlchemyAgentStore(args.database_uri)
    stored = {a.id: a.version for a in store.list(limit=1000).data}
    if stored != {key: row["version"] for key, row in before.items()}:
        raise RuntimeError("The selected database does not match the live catalogue")
    artifacts = LocalArtifactStore(str(args.artifact_location))
    for agent in store.list(limit=1000).data:
        if not artifacts.exists(agent.bundle_location):
            raise RuntimeError("Artifact directory is missing a registered template bundle")
    payload = _tar_gz_dir(args.bundle)
    report = {"action": "validated_only", "runtime": runtime, "validation": validation,
              "bundle_path": str(args.bundle.resolve()), "before": before}
    args.report.parent.mkdir(parents=True, exist_ok=True)
    with args.report.open("x") as handle:
        handle.write(json.dumps(report, indent=2) + "\n")
    report.update(update_existing(
        args.database_uri, artifacts, payload,
        expected_version=args.expected_version, expected_sha256=args.expected_sha256,
    ))
    args.report.write_text(json.dumps(report, indent=2) + "\n")
    after = catalogue(args.api_url)
    report["after"] = after
    report["unrelated_live_entries_unchanged"] = (
        set(after) == set(before)
        and all(after.get(key) == row for key, row in before.items() if key != report["agent_id"])
    )
    report["live_version_verified"] = after.get(report["agent_id"], {}).get("version") == report["version"]
    args.report.write_text(json.dumps(report, indent=2) + "\n")
    if not report["unrelated_live_entries_unchanged"] or not report["live_version_verified"]:
        raise RuntimeError(f"Template update needs inspection; see {args.report}")
    return {key: value for key, value in report.items() if key not in {"before", "after"}}


def register_new(store, artifacts, cache, payload: bytes) -> dict:
    from omnigent.db.utils import builtin_agent_id

    digest = hashlib.sha256(payload).hexdigest()
    agent_id = builtin_agent_id(NAME)
    existing = store.get_by_name(NAME)
    if existing is not None:
        if existing.id != agent_id or existing.bundle_location.rsplit("/", 1)[-1] != digest:
            raise RuntimeError("A different Penny already exists; this installer only adds a new template")
        if not artifacts.exists(existing.bundle_location):
            raise RuntimeError("Registered bundle is missing; repair requires a separate operation")
        if artifacts.get(existing.bundle_location) != payload:
            raise RuntimeError("Registered bundle content does not match its stored hash; refusing repair")
        return {"action": "already_registered", "agent_id": agent_id, "version": existing.version,
                "bundle_sha256": digest}
    if store.get(agent_id) is not None:
        raise RuntimeError("Penny's deterministic ID is already occupied")
    bundle_key = f"{agent_id}/{digest}"
    if artifacts.exists(bundle_key):
        if artifacts.get(bundle_key) != payload:
            raise RuntimeError("New artifact key is occupied by different content")
    else:
        artifacts.put(bundle_key, payload)
    if artifacts.get(bundle_key) != payload:
        raise RuntimeError("New Penny artifact failed read-back verification")
    # Create-only: a competing registration must never turn into an update.
    store.create(agent_id, NAME, bundle_key)
    cache.evict(agent_id)
    created = store.get_by_name(NAME)
    if created is None or created.id != agent_id:
        raise RuntimeError("Registration was not confirmed")
    return {"action": "registered_new", "agent_id": agent_id, "version": created.version,
            "bundle_sha256": digest}


def register(args) -> dict:
    from omnigent.runtime.agent_cache import AgentCache
    from omnigent.server.app import _tar_gz_dir
    from omnigent.stores.agent_store.sqlalchemy_store import SqlAlchemyAgentStore
    from omnigent.stores.artifact_store.local import LocalArtifactStore

    validation = validate_bundle(args.bundle)
    runtime = verify_update_runtime(args.api_url, args.database_uri)
    if not args.artifact_location.is_absolute() or not args.artifact_location.is_dir():
        raise ValueError("Use the existing server's absolute artifact directory")
    if args.report.exists():
        raise FileExistsError("Choose a fresh report path to preserve prior evidence")
    before = catalogue(args.api_url)
    store = SqlAlchemyAgentStore(args.database_uri)
    stored = {a.id: a.version for a in store.list(limit=1000).data}
    if stored != {key: row["version"] for key, row in before.items()}:
        raise RuntimeError("The selected database does not match the live catalogue")
    artifacts = LocalArtifactStore(str(args.artifact_location))
    anchors = list(store.list(limit=1000).data)
    if not anchors:
        raise RuntimeError("No existing agents found to check the artifact directory")
    for anchor in anchors:
        if not artifacts.exists(anchor.bundle_location):
            raise RuntimeError(f"Artifact directory is missing the existing {anchor.name} bundle")
    payload = _tar_gz_dir(args.bundle)
    report = {"action": "validated_only", "runtime": runtime, "validation": validation,
              "bundle_sha256": hashlib.sha256(payload).hexdigest(), "before": before}
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + "\n")
    with tempfile.TemporaryDirectory(prefix="penny-registration-cache-") as directory:
        cache = AgentCache(artifacts, Path(directory))
        report.update(register_new(store, artifacts, cache, payload))
    args.report.write_text(json.dumps(report, indent=2) + "\n")
    after = catalogue(args.api_url)
    report["after"] = after
    report["existing_agents_unchanged"] = all(after.get(key) == row for key, row in before.items())
    registered = after.get(report["agent_id"], {})
    report["live_description_verified"] = registered.get("description") == validation["description"]
    args.report.write_text(json.dumps(report, indent=2) + "\n")
    if not report["existing_agents_unchanged"] or not report["live_description_verified"]:
        raise RuntimeError(f"Registration needs inspection; see {args.report}")
    return {key: value for key, value in report.items() if key not in {"before", "after"}}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    skills = commands.add_parser("install-skills")
    skills.add_argument("--home", type=Path, default=Path.home())
    build = commands.add_parser("build")
    build.add_argument("--output", required=True, type=Path)
    build.add_argument("--profile", choices=list(BuildProfile), default=BuildProfile.DOCUMENT)
    build.add_argument("--model", default=POWERFUL_MODEL, help="Must remain gpt-6-astra; downgrades are rejected")
    build.add_argument("--effort", help="Must remain xhigh; all profiles preserve the strongest configured roles")
    build.add_argument("--model-catalog", type=Path, help="Safe local Codex models_cache.json metadata")
    build.add_argument("--claude-model-catalog", type=Path, help="Explicit Claude native model-options JSON snapshot")
    build.add_argument("--host-id", help="Host for live Claude model-options; required without a saved catalogue")
    build.add_argument("--api-url", default="http://127.0.0.1:6767", help="Local Omnigent server for model metadata only")
    validation = commands.add_parser("validate")
    validation.add_argument("--bundle", required=True, type=Path)
    registration = commands.add_parser("register", help="Add only the new Penny template to the existing local server")
    registration.add_argument("--bundle", required=True, type=Path)
    registration.add_argument("--database-uri", required=True)
    registration.add_argument("--artifact-location", required=True, type=Path)
    registration.add_argument("--api-url", default="http://127.0.0.1:6767")
    registration.add_argument("--report", required=True, type=Path)
    updating = commands.add_parser("update", help="Version existing Penny; activation requires a controlled cache refresh")
    updating.add_argument("--bundle", required=True, type=Path)
    updating.add_argument("--database-uri", required=True)
    updating.add_argument("--artifact-location", required=True, type=Path)
    updating.add_argument("--api-url", default="http://127.0.0.1:6767")
    updating.add_argument("--expected-version", required=True, type=int)
    updating.add_argument("--expected-sha256", required=True)
    updating.add_argument("--report", required=True, type=Path)
    args = parser.parse_args()
    if args.command == "install-skills":
        result = install_skills(args.home)
    elif args.command == "build":
        result = build_bundle(args.output, profile=args.profile, model=args.model,
                              effort=args.effort, model_catalog=args.model_catalog,
                              claude_model_catalog=args.claude_model_catalog,
                              host_id=args.host_id, api_url=args.api_url)
    elif args.command == "validate":
        result = validate_bundle(args.bundle)
    elif args.command == "register":
        result = register(args)
    else:
        result = update(args)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
