---
name: writing-requirements
description: Use when the Orchestrator is establishing or revising confirmed user requirements for one document workspace.
---

# Writing Requirements

Maintain the durable agreement between the user and the writing system. That
agreement records what the user requested and the raw material the user attached
to that request. It does not contain an agent's research, interpretation, plan,
or draft.

## Ownership

This skill belongs only to the Orchestrator. The Orchestrator talks with the
user and creates or updates:

```text
.draft/<workspace_id>/requirements.md
```

The workspace must already exist. Use the workspace ID and resolved target path
returned by the initialization flow. Do not choose either value, initialize a
workspace, search for an ID, or write another workflow file. Read the existing
requirements before revising them, and preserve IDs for requirements that
remain in force.

Requirements work does not investigate references, design document structure,
or draft the artifact. Investigation may help the Orchestrator resolve a
specific decision, but its findings do not become requirements unless the user
states or explicitly confirms the resulting instruction.

## Requirement authority

Every requirement must come from something the user stated or explicitly
confirmed. Record only agreements that materially govern the requested
document, including content, exclusions, intended use, form, audience, tone,
length, fidelity, or authorship boundaries when the user made them relevant.

Treat the user's request as sufficient by default. Missing ordinary writing
preferences are not missing requirements. Do not interview the user about
audience, tone, depth, structure, format, or similar choices merely because
they were not provided. Ask only when the user's material contains a conflict
or a consequential ambiguity that cannot responsibly be resolved downstream.

Do not turn conventions, likely preferences, agent proposals, reference
contents, or investigation findings into user requirements. Do not add an
assumption so that the brief appears complete.

## References

A reference is raw user-provided material associated with a requirement: for
example a URL, file path, repository location, excerpt, example, standard, or
existing draft. Always retain each user-provided reference in the `References`
cell for the requirement it supports or constrains.

- Preserve the reference sufficiently exactly for another agent to access the
  same material; keep URLs and paths verbatim.
- A cell may contain no reference, one reference, or several clearly separated
  references.
- Repeat a reference in more than one row when it genuinely applies to several
  independent requirements.
- State the intended role in the requirement itself when that role matters,
  such as sole source, example, style guide, material to transform, or material
  to compare.
- Do not replace a reference with a summary, extracted facts, a title, or a
  judgment about what it contains.
- Do not claim that a reference is authoritative, exhaustive, or factually
  correct unless the user made that part of the agreement.

If the intended role of a reference permits materially different documents and
the user's request does not resolve the choice, ask the smallest question that
does. Otherwise preserve it and let Planner inspect it.

## Authorship boundary

Capture an authorship or factual boundary only when the request establishes
one. Preserve distinctions such as faithful transformation, adaptation,
original authorship, exact preservation, and prohibition on unsupported factual
claims. A request for creative work permits ordinary creative choices; it does
not authorize invented real-world results, quotations, measurements, user
experiences, or organizational decisions.

Write the boundary as an actionable requirement rather than as an abstract
label. Never use confident phrasing to conceal a missing source or an
unconfirmed user position.

## Durable contract

Use exactly this structure:

```markdown
# Requirements

## Workspace metadata

- Workspace ID: <workspace_id>
- Target path: <resolved target path>

## Requirements

| Requirement ID | Requirement | References |
|---|---|---|
| RQ-01 | <one concrete, independently understandable user requirement> | <raw reference or None> |

## Open questions

- None
```

Use `RQ-01`, `RQ-02`, and so on. Each row contains one material agreement that
can be understood without the conversation. Use `None` when a requirement has
no reference. Do not create additional requirement tables, reference sections,
`Basis` columns, planning notes, or content summaries.

An unresolved consequential question belongs under `## Open questions`, not in
the table. Requirements are ready for Planner only when that section is
`None`. Missing preferences and ordinary planning choices are not open
questions.

## Revision

When the user clarifies the same requirement, update its row without changing
its ID. Remove or replace withdrawn instructions so contradictory historical
requirements do not remain active. Add a new ID only for a genuinely new
material agreement. Keep raw references attached to the rows they govern.

Before finishing, confirm that every row is user-authored or user-confirmed,
every supplied reference is represented in the appropriate cell, no summary or
agent assumption entered the contract, and the workspace metadata matches the
initialized workspace.
