# Intent, context, and verification for substantial writing

Use this when a document needs synthesis, has an evolving purpose, or draws on several sources. These are responsibilities, not a ceremony to impose on every message. Keep the working material compact and deliver the artifact the user asked for.

## Establish the intent

Before drafting, establish the reader's actual use for the document. Express that
purpose privately in one sentence, then decide what to keep, reframe, or leave out.
Use the following questions only where they help; they are not required output
fields or an outline to paste into the document:

- **Purpose and audience:** what this artifact enables, and what the reader needs from it.
- **Operation and scope:** draft, review, light edit, synthesis, or revision; what must remain and what is outside the task.
- **Source disposition:** which facts change this reader's understanding or next action, and which source passages are internal instructions, irrelevant history, or research commentary rather than useful content.
- **Authority and evidence:** which facts, decisions, dates, responsibilities, and external actions are supported; what is supplied but not independently verified.
- **Current corrections:** the reasons behind accepted and rejected choices, with their scope and a pointer to the user's actual words.
- **Material uncertainty:** unresolved choices that could change the result, without treating every missing detail as a blocker.

An intent agent should infer and test this brief against the conversation, not merely paraphrase the latest prompt or catalogue every source fact. Name the useful omissions as well as inclusions. The writer still receives the original request and corrections. The brief is a revisable interpretation, never a substitute for the user's words. If a real fork remains, surface that specific assumption before proceeding. Do not force personal writing, instructions, or exploratory discussion into a deliverables-and-deadlines format.

## Keep context current

Keep task facts separate from reusable writing lessons. In a sustained document task, maintain a compact working record alongside the artifact when local artifact work is authorized; otherwise keep it in the session. A new unrelated task starts with its own context. Do not create a private-data memory store as a side effect of writing.

Update the affected entries when the user corrects something, then follow the change through every dependent claim in the draft. A prerequisite confirmed complete must also disappear from gap summaries and requests to reconfirm it. Keep stable identifiers, source pointers, and the reason for the change in working context, not automatically in the reader-facing text. Distinguish current, superseded, inferred, and unresolved entries. Preserve material qualifications without repeatedly rewriting the whole context. Never reuse another task's private facts as defaults.

Useful entries include the artifact purpose, accepted outline, material claims with evidence status, open decisions, and scoped lessons. This is not a mandated schema or an extra deliverable for the user.

## Draft to the brief

Choose and organize content before polishing sentences. A requirements artifact needs what is required and what it depends on; a findings report may need the observation and evidence. Do not rewrite a source line merely to preserve it. Drop internal bookkeeping and meta-commentary unless the reader needs a procedure or audit. Put a necessary qualifier beside the fact it limits, rather than adding a general disclaimer. Incorporate an applicable lesson where it changes the artifact, not as an account of the investigation.

Do not turn “check whether this exists” into “this does not exist,” a requirement into an agreed assignment, or a suggested sequence into an estimated schedule. Names and dates are appropriate when relevant and supported. New proposals may be useful when requested, but must remain proposals.

## Review meaning and revise

Derive review questions from this artifact's purpose and risk. Use the independent assessment, challenge, and final-candidate checks in [cross-model-workflow.md](cross-model-workflow.md). Give the counterpart the original request, relevant evidence, and corrections for its independent assessment before sharing the writer's interpretation. For review, add the current brief, exact draft, and issue resolutions. Ask what a reasonable reader would take away before checking sentence-level accuracy.

Check whether:

- the artifact does the requested job and uses new evidence appropriately;
- each section earns its place for this reader, rather than reproducing the source's structure, process notes, or cautionary language;
- it implies unagreed commitments, unsupported certainty, or an operation that never happened;
- material facts, distinctions, limitations, and accepted wording survived the rewrite;
- its structure helps the intended reader and its language sounds natural;
- prior feedback has been understood semantically, including equivalent mistakes with different wording.

Use [reader-protocol.md](reader-protocol.md) for a fresh reader's first impression and evidence check. Keep claim status separate from the action: **supported**, **contradicted**, or **absent** describe the source relationship; **ship**, **revise**, or **ask** describe what to do. User-supplied facts, including facts in the draft being edited, count as source context; do not demand independent proof during a wording task. An absent source is not evidence that a capability, permission, or commitment is absent. Source-span matching can show that words occur in a source, not that the source entails a claim. A style preference is not a factual failure, and no mechanical check proves intent or tone.

Revise concrete defects and check the changed passages plus the whole artifact again, within the cross-model workflow's round limits. Close material findings with evidence; do not declare success because a tool ran or two agents agreed. Stop when no known material defect remains. If a needed source or user decision is missing, keep that limit visible instead of fabricating a pass. If successive passes make no substantive progress, identify the unresolved issue and return the usable work with that limit. Use extra passes when they resolve real issues, not to generate increasingly polished variants.

## Curate the lesson

After a correction or useful review finding, the curator proposes a small delta: the underlying principle, when it applies, why it matters, a neutral example, a boundary case, and whether the lesson is user-confirmed or inferred. Replace or supersede a mistaken lesson rather than accumulating conflicting rules. The lead checks the proposed delta against the user's actual correction.

Generalize in every role. Reusable lessons must contain no customer, employer, product, repository, environment, or personal identifiers from the task. Use neutral synthetic examples. Do not merely substitute labels into a proprietary scenario; retain only the transferable reasoning. Generalization must preserve scope: a lesson about a requirements review is not a universal ban on names, dates, or requests.

When learning is authorized, use [shared-learning.md](shared-learning.md) for the shared append-only log. Proposed lessons stay inactive until transfer and boundary tests pass and the user approves the scoped change. Do not let a curator rewrite the installed skill or propagate unconfirmed lessons to unrelated projects.

## Model and tool boundaries

Use the configured model and available tools; never infer availability from marketing names or from an empty model list. An explicitly requested model change belongs in a supported host configuration or dispatch option and must be verified there. A stronger model does not replace evidence checks, but do not dismiss the user's requested configuration without checking support.

If research is requested, inspect available read-only sources before claiming access is unavailable. If a source cannot be reached, distinguish user-supplied claims from live verification. Do not put “checked today” in an artifact unless that check actually happened. Writing does not authorize creating tasks, assigning people, sending messages, or publishing documents; keep those operations separate and report only what was done.
