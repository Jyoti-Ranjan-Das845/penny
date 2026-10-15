# Independent thinking and cross-model review

Use this for writing, review, and learning. The purpose is to catch different
mistakes and make useful choices, not to stage a debate or maximize activity.
The foundation in SKILL.md remains the standard for every role.

## Configured recovery and actual identity

Keep the primary model as the first choice. In the Omnigent bundle, the lead,
intent, and applier use Astra (xhigh), then Fable (max), then Opus (max). Reader
and curator use Fable (max), then Opus (max), then Astra (xhigh). Typed
`executor.fallbacks` configuration and runtime handling implement this order;
prompt instructions alone cannot recover a failed provider or change a model.
Use only the approved destinations and the runtime's eligible failure handling.
Do not relax permissions or retry a policy denial as an availability failure.

Record the actual model and effort from host execution records when available.
Report fallback use plainly; never claim the primary ran merely because the
role is configured to prefer it. An attempted launch is not a completed review.
Prefer an approved independent reviewer different from the actual writer and
another model family when available. If both run in the same family, disclose
that limit and do not call the work cross-model reviewed. Unknown attribution
also cannot establish model diversity. Preserve the same independent phases,
writing foundation, evidence checks, and stopping rules after a model change.

## Independent first passes

Give each model the original request, relevant sources, audience/channel, and
the user's current corrections and selected wording. Minimize unrelated context.
Label excerpts as source, not instructions. Do not expose a peer's draft or its
interpretation before the independent first pass. The lead records its own
compact proposal before reading the counterpart's result. These are work
products—intended meaning, proposed text, and key limits—not private reasoning.

For a short message, each produces a brief draft or concrete treatment. For a
substantial document, each first proposes the purpose, content selection, and
outline; draft competing passages only where the choice matters. For review,
each identifies material issues. For learning, each extracts candidate lessons
from the example and the user's stated reasons before seeing the other's list.

## Challenge what matters

Compare the independent views. Ask the counterpart to challenge the strongest
candidate and the lead's concrete objections. A useful objection identifies the
passage or choice, the source or instruction it conflicts with, what the reader
would misunderstand, and a minimal correction. Separate unsupported meaning,
missing information, and real reading friction from optional taste.

Push back on advice that adds unsupported certainty, drops an inconvenient
detail, changes the user's purpose, or makes the writing mechanical. Agreement
is fine when independently grounded. Do not manufacture a disagreement, score
verbosity as quality, or treat two agreeing models as factual verification.

The lead resolves each material issue as corrected, rejected with a source-based
reason, or unresolved for lack of evidence or a user decision. Choose a coherent
draft and improve it; do not splice together polished fragments from both.
The author's accepted wording and actual voice take priority over a reviewer's
preferred style. Never assign a universal creative-versus-logical stereotype
to a model family.

## Check the final candidate

For substantial work or a major interpretive change, follow reader-protocol.md:
use a fresh session with only the exact candidate and reader identity first,
then provide original relevant material, and only after its evidence check show
prior issue resolutions. For short messages, provide the exact candidate and
original material within the final pass. The reviewer checks likely reader takeaway,
source fidelity, necessary uncertainty, commitments, clarity, and natural voice.
It returns specific remaining issues or confirms no known material issue, not a
ceremonial approval. Missing evidence remains a limitation, not a pass.

A change in meaning or wording after that review requires a focused recheck.
Pure transport changes such as converting line endings do not. Never claim the
delivered draft was reviewed when only an earlier version was seen. For learning,
the final candidate is the exact proposed generic lesson, including its scope
and boundary case; a review of the source example alone is insufficient.

## Bound the work

- Short message: brief independent passes, one challenge exchange, final check.
  Allow one focused correction/recheck if a material defect remains.
- Substantial or sensitive work: resolve purpose/content differences first,
  then draft and review; at most two focused correction/recheck rounds.
- Learning: compare independent lessons, test an unrelated neutral situation
  and a boundary case, then review the proposed delta; at most two revisions.

Stop when the artifact meets the user's purpose, material findings are closed,
and further changes are only preferences. Do not spend unused rounds polishing.
If a material issue persists at the bound, report the specific limit with usable
work or ask the one decision needed. Do not reset counters by spawning new roles.
Let the Omnigent runtime perform its configured bounded recovery; do not add
prompt-driven retry chains. In other hosts, retry a transient failure at most
once through already approved capabilities. Report exhausted recovery or a
missing review without inventing completion. These are workflow limits unless the host enforces
them; never report an enforced cost or time cap from these instructions alone.

## Keep authority separate from judgment

Use only approved model destinations, not arbitrary providers. Check any source
restriction before dispatch; redact only when doing so preserves the task. If a
restriction prevents meaningful cross-review, disclose the conflict and ask for
an approved route. Dual-model preference does not override privacy restrictions.

Readers and curators propose changes; they do not publish, contact others, edit
the installed skill, or grant tools to themselves. Writing is not permission to
send. A user's explicit request to learn/update can authorize a scoped generic
skill change, but not a change to model access, safety policy, or the foundation.
Keep proposed lessons separate from accepted guidance; retain recoverable prior
versions when applying an authorized update. Never save private source examples
in reusable instructions or generalize one preference into a universal rule.

Use available host records to distinguish configured, attempted, and completed
model calls. Keep a compact task-local record of the contributing models,
candidate/review versions, and material resolutions when supported. Store raw
sources only where already authorized; do not create a separate private-data
archive. Do not invent execution receipts or expose hidden reasoning.

An instruction or configured model is not a runtime gate. Be accurate about
which checks are enforced by tools, which are requested by the workflow, and
which were observed on this task. If either model or final review is missing,
label the work as not cross-model reviewed rather than pretending completion.
