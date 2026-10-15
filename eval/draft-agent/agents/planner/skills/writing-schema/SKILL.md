---
name: writing-schema
description: Use when the Planner creates or revises schema.md for an established document workspace.
---

# Writing Schema

Turn the confirmed writing requirements into a document design that the Writer
can realize without rediscovering the structure.

Before designing or revising a schema, read
`references/writing-quality-north-star.md`, resolving that path relative to
this `SKILL.md`. Apply it as design criteria: make the necessary meaning
faithful, proportionate to the reader's attention, easy to follow, and
deliberately shaped for this document. It is not a source of requirements,
content, or authoring permission.

## Required state

Use the workspace ID already established for the Planner session. From the
session working directory, its durable files are exactly:

```text
.draft/<workspace_id>/requirements.md
.draft/<workspace_id>/schema.md
```

Read the current `requirements.md` before planning and the current `schema.md`
before revising. A workspace ID is not a directory root: never substitute a
`/workspaces/` path, a bundle path, or a guessed location. The requirements are
the authority for what the document must accomplish; additional context can
help realize or challenge them, but cannot silently add a new requirement.

Create or update `schema.md` at that exact schema path.

## Design the document

Treat the requirements as a complete writing brief, not as a proposed table of
contents. Understand the intended reader, purpose, scope, content obligations,
constraints, reference roles, authorship boundaries, and applicable writing
direction before choosing the design.

## Inspect referenced material

Before designing any affected part, inspect every reference in the applicable
requirements row. Use the underlying material, not a representation that merely
points toward it. A search result, link preview, metadata block, page
description, related-content card, or generated synopsis is not the referenced
source.

A consequential source claim must be traceable to a specific passage, table,
figure, or other substantive source location. A number, quotation,
attribution, named finding, or strong conclusion that appears only in a
generated overview is not established source content, even when the overview
was returned while fetching the source. Block the affected part when that
location cannot be established.

For a structured or long source, establish its substantive structure and
inspect the sections needed to cover the requirement responsibly. An initial
extraction can be useful without being complete. When it omits structure,
compresses qualifications, or selects only some topics, continue with focused
inspection until the relevant source coverage is adequate. Keep page chrome,
recommendations, and adjacent content outside the source boundary unless the
requirement explicitly includes them.

If a required reference cannot be inspected sufficiently, preserve the gap:
set the affected part to `Blocked` and identify the unavailable evidence in its
notes. Do not supply missing source content from memory, likelihood, common
practice, or another unapproved source.

Plan the document as an ordered set of coherent parts. Decide what the document
needs, how a reader should move through it, what each part accomplishes, and how
the parts depend on one another. Do not mechanically create one part per
requirement: one part may serve several requirements, and one requirement may
need several parts. Give each idea one primary home rather than instructing the
Writer to explain it repeatedly.

Choose the form of the content as part of the design. Use prose, tables,
diagrams, charts, formulas, examples, code, images, or other document elements
when they are the effective way to realize a requirement. Specify the actual
element and what it must communicate; do not add generic placeholders such as
"include a chart." Different parts may use different specification styles when
their content demands it.

Use context and referenced material identified by the requirements to make the
plan concrete. Preserve consequential facts, qualifications, source roles,
uncertainty, and authorship limits in the relevant parts. New material may help
realize a requirement only when the agreement authorizes that kind of
authorship; it does not authorize wider scope or invented factual content.

The schema settles decisions the Writer should not have to rediscover:
structure, content placement, required document elements, dependencies, and
material evidence or authority boundaries. Leave the Writer freedom over
language and composition. Write a plan, not finished prose.

## Requirement discipline

Every part must serve at least one requirement ID. Before finishing, check the
reverse direction as well: every consequential requirement has a clear home in
the schema. If a document-wide constraint affects several parts, encode it
where it governs those parts rather than inventing a content part solely to
hold the constraint.

## Create or revise

For new work, create the ordered parts needed by the requirements. For existing
work, preserve stable part IDs and change only what the new information affects.
Update relationships between parts when a change makes them inaccurate.

Set a part to `Ready` only when its specification and necessary authority are
sufficient for responsible writing. When a consequential dependency remains,
set the affected part to `Blocked`, record the dependency in `notes`, and frame
the smallest question or investigation that would resolve it. Complete the
parts that do not depend on that answer.

## Schema contract

Write `schema.md` as ordered XML-tagged parts inside Markdown:

```xml
<schema>
  <part id="P01">
    <title></title>
    <serves></serves>
    <specification></specification>
    <authority></authority>
    <status>Pending</status>
    <notes></notes>
  </part>
</schema>
```

- `id`: Stable part identifier (`P01`, `P02`, and so on). Never reuse or
  renumber an assigned ID.
- `title`: Human-readable part name.
- `serves`: One or more requirement IDs. Every part serves at least one
  requirement; a requirement may be served by several parts.
- `specification`: Free-form contract for what the Writer must realize. Include
  the content, document elements, relationships, internal order, and depth that
  matter for that part. Do not write finished prose.
- `authority`: Only boundaries that materially govern what the Writer may say
  or add. Prefix an item with `FACTUAL`, `DOMAIN`, `CREATIVE`, or `PROHIBIT`
  when that distinction matters. Do not manufacture entries to fill the field.
- `status`: Exactly `Pending`, `Ready`, or `Blocked`.
- `notes`: Concise planning note, unresolved dependency, or recorded
  resolution. Clear or mark resolved notes when they no longer apply.

Keep the parts in document order, with one `<part>` per coherent block. Do not
add fields or wrapper structures unless this contract itself is deliberately
changed.
