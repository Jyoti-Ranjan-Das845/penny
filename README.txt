Penny model backups for Omnigent — 2026-09-18

This release contains the complete Penny source and generated agent bundle,
plus the complete Omnigent source with native fallback support. It is not a
single prompt: Penny contains five roles, shared writing guidance, build and
learning helpers; the failover mechanism runs in Omnigent.

Configured order
  Lead, Intent, Applier: Astra (xhigh) -> Fable (max) -> Opus (max)
  Reader, Curator:       Fable (max) -> Opus (max) -> Astra (xhigh)

Exact model IDs
  gpt-6-astra / codex-native
  claude-fable-5-1 / claude-native
  claude-opus-5 / claude-native

Behavior
  Each role has its primary and two ordered backups. A recognized model,
  rate-limit, or provider availability failure can trigger the next candidate
  only when the runtime has positive evidence that the captured input has
  produced no model work or tool execution. Original instructions, attachments,
  role identity, and policy travel with the retry. Intermediate failures are
  withheld from the parent; the selected model is recorded and shown.

  Unknown failures, authentication/policy problems, cancellation, partial work,
  and untracked terminal-only input are not replayed automatically. A failure
  to launch a native process is surfaced as an error rather than treated as a
  proven provider outage. A successful backup remains selected for that session.
  Cross-provider permission settings use conservative native equivalents.

  This release supports fallback persistence in a single database, including
  the local SQLite installation. Split-database configurations decline recovery
  before changing state. Both native CLIs must be installed and authenticated;
  model catalog metadata alone does not prove provider availability.

Contents
  penny/             Generated agent bundle, including all five roles.
  penny-source/      Editable prompts, YAML, shared skill, Python helpers, tests.
  omnigent-runtime/  Complete modified runtime source and its tests.
  verification/      Test and installation evidence; see RESULTS.md.
  MANIFEST.json      SHA-256 inventory of all release files.
  VERIFY.py          Standard-library integrity verifier.
  runtime-existing-files.patch  Complete runtime patch against the manifest commit.

Verify the extracted archive
  Extract with a tool that preserves symbolic links. On macOS, for example:
  ditto -x -k Penny-Omnigent-Fallback-2026-09-18.zip ./unpacked
  cd unpacked/Penny-Omnigent-Fallback-2026-09-18
  python3 VERIFY.py

Build and validate Penny using this runtime
  cd omnigent-runtime
  uv sync --extra all --group dev
  .venv/bin/python ../penny-source/scripts/manage.py validate --bundle ../penny

The generated bundle requires this patched runtime; an older runtime cannot
interpret executor.fallbacks. Follow omnigent-runtime/README.md for platform
setup and penny-source/README.md for controlled template installation. The
existing Start Penny.command is a convenience launcher for the original local
installation; use scripts/start_penny.py with your own paths on another machine.

No local credentials, conversation database, private learning logs, or local backup
are included in this archive. Runtime source is supplied under its included
license. No changes have been published to an upstream repository.
