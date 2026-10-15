# Hermes Course — Build Notes

Source: "HERMES AGENT FULL COURSE 3 HOURS: Build & Sell (2026)" — Samin Yasar, 246K views.
Filtered to **architecture, context/skills management, and cost**. Sections with no build
or cost content are listed at the bottom as skipped, not summarised.

Caveat: the course funnels to a paid community. Setup content is solid; treat the
selling/pricing third (2:48:29–end) as marketing, not evidence.

---

## 1. Cost & model strategy — 8:36, 14:02, 15:01

**Subscription, not API.** This is his strongest cost point:

> "If you start out with API-based token billing… it may rack up hundreds or thousand
> dollars in credits."

- **Primary:** ChatGPT subscription (flat cost, no per-token risk)
- **Fallback:** Nous Portal — one sub covering top-tier models, image and audio,
  avoiding "200 different subscriptions"
- **Hardware:** a Mac Mini, not cloud. One-time cost, and he can see the screen.

**Per-profile speed/cost tuning (1:06:58).** Each profile pins its own model *and effort
level*. For a snappy personal agent: GPT 5.5 on **low**. Reserve high reasoning for
work that needs it.

**Overnight batching (1:28:21).** He has it ask at night whether there's a coding job to
run while "AI tokens are potentially a little cheaper, the models are more available."

---

## 2. The buddy system — 10:51

Run **Codex alongside Hermes as a repair tool**, on the same subscription.

> "Codex will be the doctor for your Hermes agent."

Not theoretical — his Telegram setup broke on camera. Hermes hung on restart, he pasted
the error into Codex, Codex fixed it. Also reachable from his phone, so he can repair a
locked Mac remotely.

**Why it matters:** cheapest possible insurance. No extra subscription, and it removes
the main failure mode for non-experts (a broken agent you can't debug).

---

## 3. Context architecture — 41:53 to 56:50

Three layers, distinct jobs.

### soul.md — how it behaves
Loaded every time it talks to you. Tone, purpose, style.
His is: get to the point, lead with answers, have opinions, support them with evidence.

**Fast setup:** paste an interview-question list and say *"interview me."* It fills its
own identity file from your answers.

### user.md — what it knows about you
Same interview output, stored as durable facts. Carries across days and weeks.

### Honcho — shared memory across tools

**The four problems he says naive memory fails at** (the most useful framing in the course):

1. **Single-session** — a preference stated 40 minutes ago still applies
2. **Knowledge updates** — new facts must *override* old ones, not sit beside them
3. **Multi-session** — work spread over Telegram, Slack, Claude Code must connect
4. **Temporal reasoning** — hardest: *when* was this true, is it still true

> "Memory is what lets the agent stop acting like a new intern every time you open the chat."

**The architecture that matters for a fleet:** Honcho is **one shared brain** sitting under
Claude Code, Codex, Hermes, OpenClaw. Everything writes to it; every tool reads from it.
Solves the cold-start problem — a new session already has context.

**Peer cards ("diachronic identity")** — separate models of each person you deal with, and
of your agents. It tracks that your manager sees you one way and a colleague another.

**Dreaming** — a fine-tuned model reasons over raw chats into structured memory, handling
contradictions and knowledge updates. (Same idea Artie built independently.)

**His warning:** "Honcho is dangerous… imagine giving all your details to one memory system
from everywhere." Mitigation: it's open source, so self-host it on the Mac Mini.

---

## 4. Profiles and squads — 1:06:58, 1:10:34

**Profile = one AI employee.** Own soul, model, memory, skills, connectors. Clonable.
He splits personal / business ops / one per client.

**Squads = a leader plus members.** His actual setup:

```
Leader:  Hermes (chief of staff — holds all context)
  ├─ Claude  → planning, product design, high reasoning
  └─ Codex   → implementing Claude's plans, coding
```

**The key architectural point:** the leader isn't commanding other *Hermes bots* — it
delegates to **other harnesses** he already pays for. Routing rules are written per member
("Claude is significantly better at design"), and each member carries its own skills.

And he didn't hand-write the config:

> "You could just go back to Hermes and then say, 'Hey, set up my team, set up my squad
> such that I have XYZ and I'm using different models for different things.'"

**Caveat on scale:** he demos a 3-member squad. The elaborate version (Jarvis) is still
*one* orchestrator delegating outward — not a roster of specialists.

---

## 5. Skills — 1:26:36

**When to make one:** whenever a process worked and you want it repeated. Research differs
daily; the *format* stays fixed. That package is a skill.

**How:** don't write it. Do the task conversationally, correct it until the output is right —
*"make sure you massage it"* — then say **"make this into a skill."**

**On skill count** — directly contradicts Artie, worth noting:

> "Having more skills isn't a problem because how it looks for skills is there's an index.
> So it's actually very efficient to have a lot of skills."

Artie deliberately kept few, arguing selection burns tokens. Samin says the index makes it
cheap. **Unresolved — an index lowers selection cost but doesn't eliminate it.** Artie's
caution is the safer default until measured.

---

## 6. The agentic workflow recipe — 1:28:21

His five steps, the reusable pattern behind every build:

1. **Agent** — start with Hermes
2. **Connect** — give it the apps it needs
3. **Massage** — iterate conversationally until output is right
4. **Loop** — put it on cron
5. **Package** — turn it into a skill

> "An agentic workflow is basically a very simple loop. It's not one prompt."

The cycle: research → curate → create → review → deliver.

---

## 7. Connectors — 1:14:52, 1:15:58

MCP / CLI / API are three ways to reach an external app.

**Composio** — one gateway to hundreds of apps, free tier, OAuth handled. Solves the part
he says is normally hardest: authentication. One MCP connection instead of dozens.

---

## 8. The /goal command — 1:32:37

`/goal` sets a standing objective with a **turn budget** (he used 20). The agent builds,
checks its own work, fixes what's missing, repeats until done.

Use when a task needs many verify-and-retry cycles. Cost control is the turn budget.

---

## 9. How he measures it — 19:07

Three metrics, and the first is the real one:

1. **Work done while away from the desk** — *"If I don't have these channels set up, it
   literally can't get a lot of work done while I'm away from my desk."*
2. **Percentage of work automated**
3. **Revenue per employee**

This is the test for whether always-on is earning its cost. Note it's an argument for
**channels** (Telegram/Slack), not for more agents.

---

## 10. Channel patterns — 19:07, 28:14

- **Solo thread** — normal conversation
- **Capture channel** — one-way inbox. *"Anything I want my Hermes to just ingest and it
  doesn't need to respond to me."* Dump links now, it knows them later.
- **Topics** — Telegram threads as parallel workspaces, one per active area.
  *"I can hop between different threads and make it work on different things simultaneously."*

One agent, many threads — cheaper than many agents.

---

## Skipped — no build or cost content

Intro / how to watch (0:00–2:44) · BotFather, Slack, iMessage click-throughs (23:00–41:53)
· Multica install (1:01:26) · Google Workspace CLI (1:18:11) · all five BUILD demos
(1:20:26–2:40) — worked examples of the recipe above, no new architecture · Jarvis HUD
cosmetics (2:41:24) · entire selling/pricing section (2:48:29–end).

---

## What to take

1. **Subscription over API** — the single biggest cost decision
2. **Codex as repair buddy** — free insurance
3. **Honcho as shared brain under all tools** — the real multi-agent substrate
4. **Squad = orchestrator delegating to other harnesses**, not a roster of bots
5. **Five-step recipe** — agent → connect → massage → loop → package
6. **Measure work done while away** — the test that matters
