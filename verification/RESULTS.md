# Verification results

Date: 2026-09-18. Runtime base: 44378d68869120134d0a2663277e38af108f625d.

The tests use controlled provider failures and the real Omnigent event routes,
runner lifecycle, and SQLite store. They do not claim a live provider outage
was induced. Catalog records prove configured model identifiers, not uptime.

## Passed checks

- Penny build, model chains, candidate provenance and writing-governance tests:
  80 passed; the generated 56-file bundle validates. All 80 tests also passed
  using Penny source extracted from the archive and importing its packaged
  Omnigent runtime. The extracted generated bundle also validates.
- Spec parsing/validation/adaptation, legacy loader, Codex failure evidence and
  bounded history conversion: 731 passed and 3 subtests passed.
- Native forwarders, Claude bridge and event delivery: 662 passed. Five extra
  Codex classifier cases also passed in the spec/evidence run above.
- Claude proof checks after the final stale-model metadata fix: 32 passed.
- Native state and store tests: 24 passed, including atomic rollback, stale
  identity rejection, idempotency and split-database refusal before mutation.
- Final real-runner fallback tests: 8 passed. Both provider directions,
  first/second backups, exhaustion, duplicate events, immediate failure before
  submission acknowledgment, original attachments/instructions, newer-input
  protection, caller cancellation, and token-scoped abort are covered.
- Final server admission/coordinator gate: 15 passed (4 real-server integration
  tests and 11 coordinator tests). New input waits through both successful
  recovery and failed-start terminal publication. Lost acknowledgments, stale
  tokens, runner state loss, bounded cancellation, and permission mapping are
  covered. These reruns supersede the initial 9 runner/server integration checks.
- Existing external-status endpoint integration tests: 9 passed.
- Existing native launch/startup/status tests: 29 passed.
- Existing native conversation-resume tests: 28 passed.
- Terminal resource tests: 51 passed. The new terminal-generation tests and
  directly related status tests also passed as a focused group of 4.
- Ruff lint, Ruff formatting, and Pyrefly on changed runtime modules pass.
  Pyrefly retains the repository's existing suppressions and warnings.

Groups overlap; these numbers should not be summed into a unique-test total.

## Pre-existing test failures

One existing terminal-resource test requires the Linux `linux_bwrap` sandbox.
It fails on this macOS host with the same platform error on both the unchanged
upstream checkout and the modified checkout. The failure is recorded in
penny-resource-tests.log and penny-baseline-platform-check.log. No change was
made to bypass the sandbox check.

Four existing native model-catalog tests also fail identically on the unchanged
base and this release. The endpoint includes provider `source` metadata, while
the tests expect rows without that metadata. Targeted runs confirmed the same
four failures in 60.41 seconds on the base and 60.31 seconds on this release.
The catalog comparison report records the assertions and source provenance.
These failures were not introduced by this change.

## Recovery boundaries

Automatic retry requires positively identified input and evidence of no model
work. It does not replay partial output/tools, authentication or policy errors,
cancellation, untracked terminal input, or a lost input after runner restart.
Native process-start failures are surfaced. Split-database installations decline
fallback before mutation. If start acknowledgments are lost, the runtime attempts
token-scoped cancellation and reports uncertainty if the outcome cannot be
confirmed; it does not blindly replay. A role's selected backup persists in the
session. Actual model identity must be used when describing independent review.

## Installed and live-checked

Penny template version 4 and all 36 changed runtime files were installed, and
Omnigent was restarted successfully. The installation preserved the previous
template artifact, existing conversations, other agents, and six unrelated
user-edited UI files. The live UI displays Penny's new model-backup description.

A synthetic writing request completed on gpt-6-astra with a completed Reader
review and claude-fable-5-1 usage recorded. The final sentence was:
"We've finished the review and will send the summary on Friday."
The session returned to idle. This verifies the normal live Lead/Reader flow;
provider failover was verified using controlled failures, not a live outage.
Structured installation and smoke-test evidence is in installation.json.
