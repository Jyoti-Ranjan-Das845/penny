---
name: document-review
description: Use when Reviewer must assess a written artifact in an established document workspace.
---

# Document Review

Review the artifact as an independent quality gate. The review tests the
artifact against the confirmed requirements, approved schema, applicable
references, and shared writing-quality contract. It does not improve the draft
by silently rewriting it.

Before reviewing, read `references/writing-quality-north-star.md`, resolving
that path relative to this `SKILL.md`.

## Inputs and authority

Use the established workspace ID to read:

```text
.draft/<workspace_id>/requirements.md
.draft/<workspace_id>/schema.md
.draft/<workspace_id>/review.md
```

Read the target artifact from the target path recorded in requirements. Read
an existing review before replacing its current assessment. Requirements are
the authority for user intent, schema parts define the planned units, and raw
references are the authority for source-dependent content. Neither schema nor
artifact is evidence that its own factual claims are correct.

Inspect each applicable reference independently. Use the underlying source,
not search snippets, previews, metadata, descriptions, adjacent cards, page
chrome, or generated summaries. For long or structured material, establish its
relevant structure and inspect the sections needed to assess coverage. If an
initial retrieval is selective or incomplete, use focused follow-up inspection
for missing sections and consequential claims. When required evidence remains
unavailable, preserve that limitation as `NOT_VERIFIED`; do not infer a pass.

Absence from a selective, condensed, or incomplete retrieval is not evidence
that a claim is absent from the source. Do not record `FAIL` merely because a
term, example, number, or passage did not appear in such a representation.
Record `FAIL` for source contradiction or unsupported material only when the
substantive source was inspected sufficiently to establish it; otherwise use
`NOT_VERIFIED`.

## Review units

Create one row for every schema part and one `DOCUMENT` row.

- A schema-part row judges the artifact content intended to realize that part.
  A missing part is a failure, not an omitted row.
- `DOCUMENT` judges cross-part requirement coverage, source boundaries,
  repetition, overall organization, terminology, and the integrated reading
  experience.

Evaluate all four dimensions for every row:

### Fidelity

Confirm that the unit satisfies its requirements and schema authority while
preserving source meaning, scope, certainty, attribution, numbers, and
qualifications. Detect unsupported additions, source-boundary leakage,
material omissions, and claims strengthened beyond their evidence. Fidelity is
non-negotiable.

### Attention economy

Confirm that each element earns the attention it costs. Detect repetition,
generic continuation, decorative complexity, misplaced detail, and
disproportionate treatment. When the user did not specify length, judge
proportion against the requested document type, purpose, and source emphasis;
do not impose an arbitrary word count.

### Coherence

Confirm that relationships, sequence, dependency, comparison, and conclusion
are legible; related material is grouped; and terminology remains stable.

### Craft

Confirm that the form and language are precise, natural, and deliberately
composed for the request rather than mechanically assembled. Craft cannot
repair missing fidelity.

## Check and verdict statuses

Each dimension in each review row is exactly `PASS`, `FAIL`, or
`NOT_VERIFIED`:

- `PASS`: no material problem was found and required evidence was available.
- `FAIL`: a concrete, correctable material problem was found.
- `NOT_VERIFIED`: required evidence could not be inspected sufficiently to
  make the check responsibly.

Derive the overall verdict mechanically as exactly `PASS`,
`REVISION_REQUIRED`, or `BLOCKED`:

1. If any required check is `NOT_VERIFIED`, the verdict is `BLOCKED`.
2. Otherwise, if any check is `FAIL`, the verdict is `REVISION_REQUIRED`.
3. Otherwise, the verdict is `PASS`.

Do not average dimensions, assign a numerical score, or let strengths cancel a
failure.

## Findings

Create a finding for every `FAIL` and `NOT_VERIFIED` cell. A finding must name
the unit and dimension, identify the exact artifact location or missing
evidence, explain the material problem, point to governing requirements/schema
and source evidence where applicable, and state the smallest adequate
correction. Do not prescribe a new document design when a local correction is
sufficient.

Use stable finding IDs (`RV-001`, `RV-002`, and so on) across review iterations
while the same issue remains. In the current report, list unresolved findings
only; record IDs resolved since the previous pass under `Resolved since prior
review`. Use `None` when there are none.

## Report contract

Create or update only `.draft/<workspace_id>/review.md` using exactly this
shape:

```markdown
# Review

## Review metadata

- Workspace ID: <workspace_id>
- Target path: <target path>

## Overall verdict

<PASS | REVISION_REQUIRED | BLOCKED>

## Checks

| Unit | Fidelity | Attention economy | Coherence | Craft |
|---|---|---|---|---|
| P01 | PASS | PASS | PASS | PASS |
| DOCUMENT | PASS | PASS | PASS | PASS |

## Findings

### RV-001 — <unit> / <dimension>

- Artifact location: <precise location or None>
- Governing contract: <requirement IDs and schema part>
- Evidence: <source pointer and relevant support, or unavailable evidence>
- Problem: <material failure or verification gap>
- Required correction: <smallest adequate correction>

## Resolved since prior review

- None
```

Do not add extra status systems, alternative verdicts, scores, or an edited
artifact. Before finishing, verify that the matrix contains every schema part
plus `DOCUMENT`, every non-pass cell has a finding, and the overall verdict is
the mechanical result of the matrix.
