# How Penny works — flow reference

Written 19 Sep 2026, from the actual configs and one observed run.
Marked throughout: **[SPEC]** = what the design says, **[OBSERVED]** = what actually ran here.

---

## 0. The shape: a star, not a chain

Only the lead dispatches. Confirmed in config: `penny/config.yaml` has
`tools.agents: [intent, curator, reader, applier]`. None of the four children
has a `tools:` block at all.

    You ──▶ PENNY (lead) ──┬──▶ intent
                           ├──▶ reader
                           ├──▶ curator
                           └──▶ applier
            (all replies come back to the lead only)

Children cannot: call each other, call the lead, load skills, read files,
fetch URLs, or use any tool. Each config carries a `deny` policy on the
`tool_call` phase. They receive text and return text. That is the whole
contract.

Consequence: **there is no pipeline.** Curator does not hand to applier.
The lead takes curator's output and separately dispatches to applier. Every
arrow between two children is really two arrows through the lead.

---

## 1. MAIN FLOW — a writing task

This is the path that actually ran (Glean article summary, session cbdd3e4e).

### Phase A — Preparation (lead, alone)

  1. Load the bundled skill               `load_skill(name="penny")`
  2. Load the shared learning log         `scripts/learning_store.py load`
     → returns active lessons + a revision number
     → an empty log is normal, not an error
  3. Gather source material               WebFetch / user-supplied text
  4. Privately identify purpose           why this person, this reader, now

Nothing is sent to any child yet.

### Phase B — The lead drafts FIRST

The lead writes its own candidate before any reviewer sees anything.

**Why the order matters:** if the reader spoke first, the lead would anchor
to it, and you would get one opinion wearing two hats. Independence is
manufactured by sequence, not by instruction.

[SPEC] says step 1 is actually: send the request to the counterpart for an
INDEPENDENT pass *without* the lead's draft, while the lead forms its own
candidate in parallel. Both then compare.
[OBSERVED] the lead drafted, then sent the draft for review. Simpler, and
it collapses the independent pass into the review pass.

### Phase C — Reader dispatch

    lead ──▶ sys_session_send(reader, task + source + draft) ──▶ reader
    lead ◀── sys_read_inbox ◀── findings ◀────────────────────── reader

The lead ends its turn and waits to be woken. It must not poll.

[OBSERVED] reader returned 6 findings. 4 matched the lead's own pass.
2 were new and real:
  - lead had inverted a comparison (retrieval vs *context window size*,
    which it had framed as *model size*)
  - lead had invented a mechanism the source never states

### Phase D — Revise and deliver

The lead repairs the draft against the findings and delivers **one coherent
result**. Coordination stays out of the reply. Any text changed after review
is supposed to be re-checked.

---

## 2. THE THREE READER PASSES — spec vs reality

This is the biggest gap between design and practice.

[SPEC] `references/reader-protocol.md` defines three distinct passes:

  1. COLD TAKEAWAY — reader gets ONLY the draft and a line naming the
     intended reader. No sources, no intent, no hint of expected defects.
     "What would you believe? What would you do? What did anyone commit to?"
     This result is committed BEFORE evidence is revealed.

  2. EVIDENCE CHECK — now give the source. Every material claim is marked:
       Supported   — source licenses this meaning AND this strength
       Contradicted— source says otherwise; cite both passages
       Absent      — source does not settle it (a gap, not auto-reject)
     Verdict is separate from status: **ship** / **revise** / **ask**

  3. AFTER REVISION — fresh session, cold takeaway again, then compare old
     and new findings: fixed? new problem introduced? facts survived?

[OBSERVED] **one combined pass.** The reader got task, source, and draft
together in a single dispatch. No cold reading happened.

Why it matters: cold reading is the only pass that catches "this text is
technically accurate but a reader would conclude the wrong thing." Handing
the source at the same time as the draft destroys that.

---

## 3. SUBFLOW — Intent (optional)

    lead ──▶ intent ──▶ purpose/source analysis ──▶ lead

For substantial, ambiguous, or shifting briefs only. Explicitly **not**
mandatory: "not mandatory busywork for a short reply."

[OBSERVED] never ran. For the Glean summary the lead judged it unnecessary —
which is the lead correctly deciding a role had not earned its cost.

An intent brief is a *hypothesis grounded in the source*, not licence to
invent facts.

---

## 4. SUBFLOW — Learning (never run here)

Triggered when you ask Penny to learn something or correct it durably.

    Step 1  lead + curator EACH extract a lesson independently
    Step 2  curator writes transfer + boundary scenarios
            AND their expected outcomes, BEFORE any test
    Step 3  lead ──▶ applier, fresh title, sending ONLY:
                       the lesson, its scope, the scenario
            NOT sending: the original example, the expected answer,
                         the diagnosis
    Step 4  applier's raw output ──▶ curator, graded against the
            expectations it wrote in step 2
    Step 5  reader checks the exact proposed lesson text
    Step 6  ── YOU approve ── only then does it enter the log

**Why applier is blind:** if it saw the original example or the expected
answer it would pattern-match instead of applying the lesson. Blindness is
the entire experiment. Remove it and the test proves nothing.

Storage: `~/.penny/learning.jsonl`, shared across Codex / Claude / Omnigent.
State machine: feedback → proposal → tested → accepted.
Rejections, supersessions and revocations are retained, never deleted.
Unrun or failed tests stay pending. Never invented as passes.

Correcting a draft is NOT approval for a durable lesson. Separate decision.

---

## 5. STOPPING RULES

  - one independent / challenge / final-check sequence
  - at most 1 focused correction+recheck for a short message
  - at most 2 for a document or a lesson
  - stop earlier when nothing material remains
  - at the bound: surface the gap or the decision needed — do not force
    agreement and do not keep polishing

These are instructions to the model, **not** a host spend cap. Nothing
enforces them but the model's own compliance.

---

## 6. WHAT IS ENFORCED vs INSTRUCTED

ENFORCED by the runtime (cannot be talked around):
  - children have no tools — `deny` policy on tool_call phase
  - build validation requires exact model chains and child policies
  - `yolo: false` disables automatic approval bypass

INSTRUCTED only (model compliance, no guarantee):
  - the cold-reading protocol
  - cross-model review actually happening
  - round limits
  - reporting the true model that ran

The README states this plainly: these are "not a trusted runtime delivery
gate." Do not call a prompt-level check fail-closed enforcement.

---

## 7. KNOWN BREAKAGE IN THIS INSTALL

  - Omnigent 0.10.0 silently DROPS `executor.fallbacks` and
    `reasoning_effort`. Measured: both ABSENT on all five roles.
    → no failover. If Opus fails mid-task the role dies.
    → every role runs at default effort, not the configured medium.

  - Model identity is unverifiable. `sys_list_models` returns
    `"verified": false` — subscription logins expose no model-listing API.
    The catalog lists `claude-fable-5`; the config says `claude-fable-5-1`.
    → Penny's instruction to "report the actual model" cannot be satisfied.

  - A false "produced no output" inbox sentinel appeared once. The reader's
    report HAD landed. The lead announced a retry, then found it.
    → risk of discarded reviews or double dispatch.

---

## 8. TEST COVERAGE SO FAR

  ran:        lead, reader, skill load, learning-store load,
              one full dispatch → findings → revision cycle
  never ran:  intent, curator, applier, the learning loop,
              cold reading, fallback switching,
              any task with a deliberate planted error

One successful multi-agent run. Enough to show it is not broken.
Not enough to call it reliable.
