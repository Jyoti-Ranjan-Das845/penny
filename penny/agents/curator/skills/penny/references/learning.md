# Learn the essence of writing the user likes

Use when the user offers an example to learn from, especially with an explanation
of why it works. Treat that explanation as primary evidence. The task is to
understand the writing choices, not to mine subject-matter facts or imitate a
handful of visible mannerisms.

## Use a powerful model

Use the user's requested, verified high-capability model for this analysis even
when the example is short. In an agent host, configure or dispatch the intent
and curator roles with that model before analysis. Do not infer the model from
the agent's name or claim to have changed a running session's model. If the
requested model is unavailable, disclose that limit; do not silently substitute
a routine tier and report that the requested analysis occurred. The portable
skill does not require any particular vendor or hardcode an unavailable model.

## Extract choices and their effect

Use the independent first-pass and final-candidate checks in
[cross-model-workflow.md](cross-model-workflow.md). The lead and counterpart
extract lessons separately before comparing them. Challenge overgeneralization,
unsupported interpretations of the user's taste, and conflicts with the confirmed
foundation. Review the exact proposed lesson—not just the original example—before
an authorized update. If the counterpart is unavailable, disclose the incomplete
review and keep the lesson a proposal rather than silently promoting it to guidance.

Identify the purpose and reader; what the writer includes and leaves out; the
order of ideas; what is said directly versus left implicit; and how tone, rhythm,
specificity, or an imperfection helps. Connect each useful observation to its
effect on the reader. Not every dimension will matter in every example.

Separate what the user explicitly likes from your interpretation. Do not invent
their reason. If the user likes concision, investigate what made the short text
work; do not simply derive “make every message shorter.” Preserve inconvenient
facts and qualifications that helped the original remain honest.

## Generalize without erasing context

Propose a small lesson with:

- the underlying choice and why it helps;
- circumstances where it is useful;
- a boundary case where another choice is better;
- a neutral synthetic illustration if it clarifies the lesson;
- whether it is user-confirmed or inferred, and which existing lesson it refines.

Every role—intent analyst, writer, reader, and curator—must distinguish the
transferable principle from the source's subject matter. Reusable guidance
contains no real company, customer, product, person, repository, endpoint,
document title, or proprietary scenario from the example. Do not preserve a
private narrative with the names merely removed. Retain a local source pointer
only in authorized task context if traceability is needed; do not ship it in
the generic lesson collection.

## Test transfer before accepting a lesson

Use an incremental generation, reflection, and curation loop: retain useful
guidance, change the affected lesson, and test the change rather than rewriting
the whole playbook. This is ACE-inspired, not proof that an example generalizes.
Compare against accepted lessons before adding one. Refine or supersede an
existing lesson when appropriate; propose revoking one that no longer helps.
Do not accumulate duplicate advice or promote reviewer taste into user preference.

Before testing, the curator writes two neutral scenarios and expected effects:
one where the proposed lesson helps and one where applying it mechanically would
be wrong. A fresh **Applier** receives only the lesson, its scope, and one scenario
at a time—not the original example, preferred answer, expected effect, or curator's
diagnosis. It produces the requested text, without grading itself. Use separate
fresh contexts for the transfer and boundary cases.

The curator or an independent reviewer compares those actual outputs with the
prewritten expectations. Check meaning, reader benefit, voice, and material facts;
do not grade by phrase matching. Record the output and actual model/effort in
task-local evidence. A configuration is not a run. If either case fails, revise
the lesson and rerun within the round limit; otherwise keep it pending. Test a
clean control too when the lesson could make the writer remove legitimate content.

Keep the confirmed foundation in `SKILL.md` when comparing new advice with
existing guidance. A new example or another model's proposal is not authority
to override it. Test whether an addition makes the reader's job easier while
preserving meaning; more rules or more polished wording are not improvements
by themselves. Raise a genuine conflict for the user's decision.

For rejected writing, distinguish a wording problem from a content-selection
problem. If the passage did not belong, generalize the decision to omit it rather
than collecting phrases to ban. Test a different purpose where similar material
is useful, such as a requested procedure or evidence review. Apply this to every
role's guidance, not just the final writer's vocabulary.

When learning is authorized, use [shared-learning.md](shared-learning.md). Record
generalized feedback, then a scoped proposal with both test results. Only an
explicitly approved, passing proposal becomes active. Correct the current draft
without waiting for global approval; do not confuse that repair with shared
learning. Keep raw private examples out of the log and installed instructions.

For feedback, show the essence in a few plain sentences when useful; do not
turn every example into an elaborate analysis report. Record and report what
was actually learned, tested, and saved, including any remaining uncertainty.
