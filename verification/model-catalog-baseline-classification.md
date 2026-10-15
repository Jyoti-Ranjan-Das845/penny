# Native model catalog baseline comparison

All four catalog assertions fail identically on the final fallback worktree and clean base commit `44378d68869120134d0a2663277e38af108f625d`. They are confirmed baseline failures, independent of the fallback change.

| Source | Result |
| --- | --- |
| Final worktree | 4 failed in 60.31s |
| Clean base git archive | 4 failed in 60.41s |

The assertion failure blocks match exactly, including test locations. Both runs imported `omnigent` from their intended source tree, verified in the logs. They used the final worktree's existing Python environment with `PYTHONPATH` set to the respective source root. No installed runtime or live session was changed.

The existing model-options endpoints add provider `source` metadata to each row. These test expectations omit that field. The Claude failures explicitly show the extra `source` value (`kind: subscription`, `label: Subscription`, `name: claude`); Codex uses the same row-decoration helper. The test module, model catalog module, both endpoint implementations, and both source-decoration helpers are unchanged from the base commit. This is an existing response-contract expectation mismatch.

Exact failing cases, all in `tests/runner/test_app_sessions_native_events_lifecycle.py`:

- `test_codex_native_model_options_query_model_list[unset-keeps-codex-default]`, assertion at line 1018.
- `test_codex_native_model_options_query_model_list[launch-model-wins]`, assertion at line 1018.
- `test_claude_native_model_options_use_session_launch_catalog`, assertion at line 1145.
- `test_claude_native_model_options_serves_probe_rows_after_pending`, assertion at line 1262.

Both runs used `/Users/Pradeep.Das/Spaces/aiv/workbench/omnigent-penny-fallback/.venv/bin/python -m pytest`, followed by those four fully qualified node IDs and `-q --tb=short --show-capture=no`. The complete command and source-import provenance are in each log.

Sanitized logs retained in this folder:

- `model-catalog-final-comparison.log`
- `model-catalog-baseline-comparison.log`

The outputs were checked for authorization credentials, API keys, JWTs, access tokens, client secrets, and passwords before copying; no matching credential values required redaction. Source comparison additionally confirmed identical ASTs for `_model_configuration_source`, `_with_model_configuration_source`, `get_session_codex_model_options`, and `get_session_claude_model_options`.
