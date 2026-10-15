# Review: Q3 Platform Reliability Update

## What a reader actually takes away

Read it cold, as someone on the team: *uptime was 99.7%, and we're told that's good news.* That's the only fact in the email. Everything else is framing. Nothing to remember, nothing to do, nothing to hold anyone to.

That's the core problem. This is a reliability update that doesn't report on reliability.

## The specific problems

**1. The one number is unanchored.** "Uptime reached 99.7%, representing progress toward our target." What's the target? What was it last quarter? 99.7% is about two hours of downtime a month — depending on your SLO, that's either a solid quarter or a miss. "Progress toward our target" is a phrase people use when they missed it. If you missed, say the target and say you missed it; the hedge is more damaging than the number.

**2. Two claims with no measurement at all.** "Reduced mean time to recovery and enhanced our observability tooling." Reduced from what, to what? MTTR is a number — you have it. "Enhanced our observability tooling" could mean you adopted distributed tracing or that someone added a dashboard. Unquantified improvement claims read as *nothing happened here*, which may be unfair to real work.

**3. No incidents.** This is the biggest credibility gap. Your audience is the team — the people who got paged. They know what broke in Q3. An email that describes the quarter as uninterrupted progress, written to the people who lived through the outages, invites them to discount everything in it. Name the significant incidents, what caused them, and what changed as a result. That's the part of a reliability update people actually read.

**4. The first paragraph can be deleted with zero loss.** "I'm pleased to share that we've made significant strides in our reliability posture… through concerted cross-functional effort… meaningful improvements across several key dimensions." It announces that there's good news before giving any, and it uses four abstractions ("strides," "posture," "concerted," "dimensions") to say nothing. Readers learn from paragraph one that this email won't be dense, and they start skimming.

**5. "Looking ahead" commits to nothing.** "We'll continue to prioritize reliability as a core tenet of our engineering culture" has no owner, no target, no date, and no specific work in it. If there's a Q4 reliability goal, that sentence should be the goal. If there isn't one yet, say when there will be.

**6. The thanks doesn't land.** "Thank everyone for their dedication and hard work" thanks no one. If a specific team absorbed the on-call load or a specific person drove the MTTR work, name them. Otherwise the line is just the shape a closing paragraph makes.

**7. "More to come" is a non-ending.** It promises a sequel with no date. Either say when the next update lands or cut it.

**8. Stock phrases to strike:** "reliability posture," "concerted cross-functional effort," "meaningful improvements across several key dimensions," "core tenet of our engineering culture," "in service of our customers." Each one is doing the job a plain word could do better, and together they're the main reason this reads as generated rather than written.

**9. Every paragraph has the same shape** — a soft claim followed by a softener. That sameness is why it feels templated even where the content is fine.

**10. The subject line is accurate but tells no one anything.** "Q3 Platform Reliability Update" is a filing label. If the quarter had a headline — you hit the SLO, you missed it, you cut MTTR in half — put it in the subject.

## What to fill in before you rewrite

You'll need these numbers in front of you, and most of this email is just them:

- Uptime target, Q3 actual, Q2 actual
- MTTR before and after, and the specific change that moved it
- The Q3 incidents worth naming, with cause and fix
- What "observability tooling" concretely means — what you can see now that you couldn't in Q2
- The Q4 reliability goal, with an owner
- Whether 99.7% is a hit or a miss, stated plainly either way

## One structural suggestion

Lead with whether you hit the target. Then the two or three concrete things that changed, each with its number. Then the incidents and what you learned. Then the Q4 goal. The "pleased to share" and "more to come" don't need replacements — the content does the work those sentences were standing in for.