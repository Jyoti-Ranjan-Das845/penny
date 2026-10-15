# One learning log, shared locally

Codex, Claude Code, and Omnigent on the same account use `~/.penny/learning.jsonl`.
Resolve the helper relative to this skill directory, not the current project.
The same helper is bundled with the Omnigent agent. It has no third-party Python
dependencies. Do not create a competing log in each project or host installation.

## At the start of each task

Run `python3 <skill-directory>/scripts/learning_store.py load`. For scoped lessons,
pass `--input <context-file>` containing, for example,
`{"context":{"channel":"email","purpose":"status"}}`. Use the actual task's
context values. The output explicitly lists `scoped_out` lessons that did not
match; reread with appropriate context when one might apply. Do not silently treat
a scoped-out lesson as absent or broaden its scope yourself.

Use only `active_lessons` as accepted guidance and only where each lesson's
`applies_when` fits. Respect `does_not_apply`. The latest user request and the
confirmed foundation still govern. Pending entries are material for curation,
not instructions to apply. Keep the returned `revision` in internal run evidence
and supply the same relevant snapshot to child roles. A later task reloads it;
do not reuse a stale snapshot across turns.

If the helper is inaccessible or rejects the log, report that shared learning
was not loaded and work from the current conversation. Do not repair or replace
the log automatically. A missing log produces a valid empty result. The existing
legacy notes file is not imported automatically; it may contain private material
and unchecked lessons.

## Capture, test, approve

When the user asks to teach or update Penny, use the helper's `feedback` command
to record a generalized observation and their reason. Then follow `learning.md`:
extract the essence with a verified powerful model, compare existing guidance,
test transfer and boundary in fresh contexts, and present the scoped lesson for
approval. After approval, use `accept`. Never accept your own inferred rule simply
because it passed two tests. A previously explicit user instruction can be cited
as approval for that exact scope; do not stretch it to adjacent preferences.

All mutations accept a JSON object via stdin or `--input <file>`:

- Common: `source_host` (such as `codex`, `claude`, `omnigent`), optional stable
  `event_id` for safe retries. Reusing an ID with changed content is an error.
- `feedback`: `summary`, `reason`, optional `scope` object.
- `propose`: `feedback_ids`, `lesson`, `applies_when`, `does_not_apply`, `dimension`,
  `curator_model`, `tests`, optional `scope` and `supersedes` (active proposal ID).
  Curator model must be the verified `gpt-6-astra` or `claude-fable-5-1`, not a role
  label. `tests` has `transfer` and `boundary`, each with `status`, `scenario`,
  `expected`, `observed`. Status is `pass`, `fail`, or `untested`.
- `accept`: `proposal_id`, `approval` (the explicit user authorization).
- `reject` or `revoke`: `proposal_id`, `reason`. Rejection closes a pending
  proposal; revocation deactivates an accepted one without deleting history.

An Opus fallback can contribute task-local analysis, but the store's approved
curator identities remain unchanged. Keep that contribution pending until a
verified Astra or Fable independently checks the exact lesson and test evidence.
Record that actual checking model as curator only after it runs; preserve the
Opus contribution in authorized task context. Never relabel an Opus run as Fable
or Astra to pass validation. If neither approved checking model is available,
keep the proposal outside the durable store and disclose the remaining check.

Use `events` for an authorized audit, not as the default writing context. Exact
scope/dimension matching is required for supersession. Revoking a successor does
not silently revive the old lesson. Resolve a genuine scope change with the user.

The log contains only generic writing choices, scope, and neutral tests. Do not
save company or customer names, products, personal identifiers, source documents,
private narratives, credentials, or executable instructions. Do not merely rename
a private scenario. The helper validates schema, not privacy or semantic truth;
every role and the lead must check generalization before a write.

## What code does and does not guarantee

The helper locks concurrent access, validates the full event history, writes
append-only events with restrictive new-file permissions, and returns a hash of
the exact log. It rejects invalid transitions, duplicate-ID conflicts, acceptance
without reported passing tests, and corrupt/truncated logs. It refuses logs over
16 MiB rather than silently truncating them. Code can reproduce the same active
state from the same history; timestamps and new IDs are intentionally variable.

Calling the helper before writing is an instruction-level requirement, not a
verified native-host hook. Model identity, test results, and approval text are
caller-reported; the helper cannot attest them. A valid record does not prove a
lesson is sound or that a draft follows it. Actual outputs still need review.
Do not describe this as deterministic prose or a formally verified writing agent.

This is a local-account design. A remote/shared host has a different home directory
and needs explicit per-user storage and access control. Do not point everyone's
agents at one person's preferences or silently synchronize private material.
