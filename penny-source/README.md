# Penny

**Write like a thoughtful person speaking plainly.**

Penny is a generic writing partner for messages and documents. It understands
what the artifact needs to accomplish, selects the right content, preserves
the author's voice, and checks what the reader will take away.

No real company, product, customer, or proprietary example belongs in the
portable guidance. Task facts stay in their own authorized context. Lessons
are generalized with scope and counterexamples, not turned into universal
rules about names, dates, informality, or document structure.

## Common skill and agent

- Codex and Claude Code discover the same `skills/penny` source through their
  local skill directories. Invoke `$penny` or `/penny`, respectively.
- The Omnigent bundle adds an intent analyst, reader, curator, and blind lesson
  applier. Each receives
  the same portable guidance. Prefer both model families even in short tasks;
  actual fallback attribution determines whether that diversity was achieved.
- Learning starts with independent analysis, preferably Astra and Fable. The user's reason
  for liking the writing is primary evidence; inferred lessons remain proposals.

The shared skill describes the same protocol for either native host. It cannot
grant access to another provider: use supported delegation or an already
authorized bridge. If the counterpart is unavailable, disclose incomplete
cross-model review; do not pretend a local self-check was an independent review.

The Omnigent configuration is quality-first:

| Role | Primary → backup 1 → backup 2 | Work |
| --- | --- | --- |
| Penny | Astra / xhigh → Fable / max → Opus / max | Independent assessment, writing, resolving objections |
| Reader | Fable / max → Opus / max → Astra / xhigh | Independent proposal, challenge, exact final-candidate check |
| Intent | Astra / xhigh → Fable / max → Opus / max | Additional purpose/source analysis for complex work |
| Curator | Fable / max → Opus / max → Astra / xhigh | Independent essence extraction and transfer tests |
| Applier | Astra / xhigh → Fable / max → Opus / max | Fresh-context application without the original example or expected answer |

Exact model IDs are `gpt-6-astra` (`codex-native`), `claude-fable-5-1`, and
`claude-opus-5` (both `claude-native`). Each executor declares its two backups in
typed `executor.fallbacks` entries containing `model`, `harness`, and
`reasoning_effort`. Runtime support is required: prompt instructions cannot
recover provider failures. The builder requires all three identities in the
host catalogs and checks adapter effort support for every candidate. It rejects
missing or changed chains, unavailable catalog entries, and older runtimes that
cannot preserve the typed fields. The manifest records each candidate and its
evidence limits; it does not attest live provider execution.

Keep primary models preferred. Report the actual model when a backup runs and
prefer an approved reviewer different from the actual writer. Recovery may leave
both in the same family; disclose that limit without claiming cross-model review.
The runtime bounds eligible recovery; prompts must not introduce extra retry
chains or bypass policy denials. Explicit `yolo: false` and Claude's
manual permission mode disable automatic approval bypass, not all possible
side effects or all host access.

Recovery is limited to console/API inputs captured and persisted by the runner.
Model unavailability, rate limits, and provider unavailability can trigger the
next candidate only with proof that no output or tool work occurred. Unknown
failures, authentication errors, policy denials, and failures after work do not
authorize replay. Direct terminal typing without a captured input is outside
this recovery path. A startup error is not by itself proof of a safe retry.
The replacement retains the original role, instructions, skills, tools, and
policy binding; it receives prior history before the captured input, then that
input once. Runtime tests and a generated bundle do not establish live provider
recovery until that path is actually exercised.

## Dynamic configuration

The shared skill now includes a standard-library learning helper. All three
local hosts use `~/.penny/learning.jsonl`: generalized feedback → tested proposal
→ explicit approval → active scoped lesson. Rejections, supersession, and
revocations retain history. A fresh load returns the accepted state and exact
log revision. See [the operational protocol](skills/penny/references/shared-learning.md).

This is an ACE-inspired incremental context loop, with blind transfer and
boundary tests. It is not deterministic prose. The helper enforces storage and
state transitions; semantic quality, generalization, and reported test/approval
evidence still need judgment. Invoking the loader before each task is currently
instruction-driven in all three hosts, not an automatic native-runtime hook.
Remote/shared-server use needs explicit per-user storage, not one account's log
shared indiscriminately. No remote synchronization is installed.

The build command generates a fresh, validated bundle from typed options.
Profiles describe task size, not business subject matter or a weaker model:

- `message`: brief independent contributions and a short review loop.
- `document`: purpose/content assessment before drafting; the default.
- `learning`: independent lessons, scope challenge, and transfer tests.

All profiles retain the exact ordered chains above. The actual request determines
which additional roles are useful. Unsupported choices fail; the generator does
not silently choose a weaker model. Claude's model-options catalog does not
advertise per-model effort: the manifest labels its effort evidence as adapter
support, with execution verification still separate.
A generated config takes effect when a session is launched or the installed
template is explicitly updated. Runtime recovery may start a configured backup
after an eligible failure; editing this source does not change a live session.

Use the Python interpreter from an Omnigent environment with typed fallback support:

```sh
python scripts/manage.py build --output /absolute/fresh/penny --profile document --host-id YOUR_LOCAL_HOST_ID
python scripts/manage.py validate --bundle /absolute/fresh/penny
```

See `python scripts/manage.py build --help` for exact model/catalog options.
A previously fetched local Claude model-options JSON can be supplied with
`--claude-model-catalog /absolute/catalog.json` instead of a host ID. Offline
metadata does not establish that a model is currently reachable. A display name
alone is insufficient.

Penny itself writes and coordinates. Reader participates in every writing task;
curator supplies the independent first pass for learning, followed by a
reader check of the proposed lesson. Intent is optional extra analysis, not a
substitute for the other model. Do not add all roles to every simple message.

## Intent, writing, review, learning

Both independent contributors receive the original request and relevant sources before seeing
each other's proposed answer. They independently identify the intended meaning
and useful treatment. The lead then exchanges concrete objections with the
counterpart and resolves them against the sources and reader's needs. Agreement
is allowed; confidence or a majority is not evidence. Do not splice together
the most polished sentences from competing drafts.

The reader checks the exact final candidate for meaning, evidence, unintended
commitments, natural voice, and reader takeaway. Text changes after review need
a focused recheck. A fresh final reader is preferred for substantial work.
Missing evidence remains a limit; no pass is fabricated to end the loop.

The curator extracts small, scoped lessons and tests transfer and boundary cases.
It returns proposed context or lesson updates to the lead, which verifies them
and applies only authorized changes. Raw private examples are not saved in the
generic lesson collection. The agent does not silently edit its own installation.
The shared learning store still requires verified Astra or Fable curation. An
Opus contribution stays task-local until one of those models independently
checks the exact lesson and test evidence; do not mislabel the actual model to
pass validation.

Three loops cover the work:

1. Independently assess, challenge concrete choices, draft/revise, and check the
   actual final candidate.
2. Incorporate feedback into the affected parts of the brief, revise, and check
   the whole artifact for regressions.
3. Extract a principle from an example and the user's reasons, test transfer and
   limits, then retain only the authorized generic lesson.

Stop when known material defects are resolved. Allow at most one focused
correction/recheck for a short message and two for a document or lesson, rather
than polishing indefinitely. If a material issue remains, report it or ask the
specific decision needed. These round limits are instructions, not a hard spend
cap. More calls have not been shown to improve every writing task.

## Governance: what is enforced and what is instructed

- Child roles have a deny-all tool-call policy. The builder embeds exact
  role-relevant excerpts of the shared guidance, including its foundation;
  the full identical skill is bundled, and the lead supplies any additional
  relevant guidance in the task message. They do not load skills or read files.
  Oversized native launch instructions are rejected. Children can return
  text, not edit files, publish, retrieve other data, or delegate. Native and
  Omnigent tool denial still need verification on the actual deployment.
- Build validation requires the exact primary and two-backup chain for every role,
  complete candidate evidence, disabled approval bypass,
  matching shared guidance, and child policies. The update tool retains its
  prior-version/hash checks and recoverable old artifact.
- Diverse-model participation, original-context handoff, final-candidate review,
  and round limits are workflow requirements. They are not a trusted runtime
  delivery gate. Execution traces must show what actually happened; do not call
  a prompt-level check tamper-proof or fail-closed enforcement.
- The root is not fully tool-isolated. Drafting does not authorize sending or
  changing installed guidance. A curator proposes; the user authorizes a scoped
  durable change. These instructions do not turn the root into a sandbox.
- Provider/data restrictions take priority over dual review. Do not route
  restricted sources elsewhere to complete the pair, save raw examples as
  reusable guidance, or invent a review when either model is unavailable.

The function policy currently requires Omnigent's trusted local-operator bundle
path. Default untrusted-upload validation rejects the dotted policy handler;
do not disable that protection on a shared server merely to install this bundle.

No global Omnigent policy, other agent, live template, or installed shared skill
is changed by building or staging Penny. Explicit installation is separate.

## Install and update

```sh
python scripts/manage.py install-skills
```

This creates collision-safe discovery links to the common source. Use a new host
session if its skill list or loaded instructions are already cached.

The standalone skill package contains only the `penny/` skill folder. It can be
installed in Claude Code's skill directory or Codex's shared skill-discovery
directory without the Omnigent agent. Local installations link to the same
canonical source; a copied ZIP on another machine needs an explicit update when
the source changes. The skill does not change the host's active model by itself.

`register` remains create-only. `update` is an explicit versioned operation with
expected-state checks and a preserved old artifact. Neither should be confused
with activation in an already-running server: the live cache must be refreshed
through the supported server lifecycle.

Updating the existing template preserves conversation history and the other
agents. Existing conversations may use the new template behavior when resumed;
they are not frozen copies. Do not restart the server while unrelated work is
running. See command help and the update report for activation status.

For a staged release, fully stop local Omnigent yourself, then run the local
`Start Penny.command` convenience launcher. It checks that both the host daemon
and server are stopped, validates the installed `penny` bundle, and starts
Omnigent with that bundle selected for startup registration. It never stops an
existing process. The generic helper is `scripts/start_penny.py --bundle
/absolute/path/penny`; use the running installation's Python interpreter. The
directory must be named `penny` because the host derives the builtin name from
that directory. An ordinary restart alone does not import a newly staged bundle.

The local launcher is machine-specific and is not included in the portable skill
or agent archives. Startup registration retains the existing Penny ID and old
artifact. A successful build or preflight does not prove live activation; check
the new version, description, model execution, and visible picker after starting.

The installed short picker label is **Penny — Multi-agent writing**. Some host
versions hardcode these labels. The optional `install_picker_label.py` is a
version-specific compatibility patch, not part of the generic skill; it saves a
backup and refuses unknown builds. An upgrade may replace it. Hard-refresh the
browser after an asset change and verify the actual dropdown.

## Validation

```sh
python -m unittest discover -s tests -v
```

Structural tests cover installation, generated configuration, bundle discovery,
unsupported model/effort rejection, and safe registration/update boundaries.
They do not establish writing quality or live model execution.

`tests/behavior_cases.json` contains neutral semantic regression cases and
positive controls. Independent forward tests should generate outputs before
consulting the review questions. Evaluate purpose, meaning, source fidelity,
and transfer—not exact wording. Keep deployment, provider execution, and writing
behavior evidence distinct.

## Layout

```text
skills/penny/       generic, portable guidance and neutral examples
omnigent/          lead, intent, reader, curator, and blind applier configuration
scripts/           installation, configuration generation, validation
tests/             structural tests and semantic test cases
evidence/          local verification reports, not part of the skill
```
