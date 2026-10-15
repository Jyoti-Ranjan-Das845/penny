import json, pathlib
T=pathlib.Path("tasks"); G=pathlib.Path("ground_truth")
def tr(f, lim):
    d=json.load(open(f)); turns=d["meeting_transcripts"][:lim]
    return "\n".join(f"{t['speaker']}: {t['content']}" for t in turns), d["general_query_list"][0]["answer"]
tasks=[]
for tid,f,instr,lim in [
 ("01","src-ES2004a.json","Summarize this product design meeting for someone who missed it.",320),
 ("02","src-covid_4.json","Summarize this parliamentary committee session on COVID-19 for a policy reader.",120),
 ("03","src-education_13.json","Summarize this education committee session for a colleague who needs the substance, not the procedure.",110),
 ("04","src-IS1003d.json","Summarize this meeting. It is long and rambling; give the reader what actually got decided.",300)]:
    src,ref=tr(f,lim); tasks.append((tid,"summarize",instr,src)); (G/f"task-{tid}.md").write_text(ref)

tasks += [
("05","draft","Write a Slack message to the engineering channel.","""NOTES (mine, messy):
- deploy went out 14:20, rolled back 14:52
- cause: migration 0047 ran twice because the runner retried on a timeout
- 40,000 duplicate rows in `orders_audit`
- restored from 02:00 snapshot, no customer-facing data lost
- Priya spotted it from the latency alert
- fix: idempotency key on migrations, she's got a branch up
- postmortem Thursday, I'll send an invite"""),
("06","draft","Write a short requirements note from this conversation, for the team doc.","""CONVERSATION (verbatim):
Me: we need the export to handle files over 2GB, it dies right now
Sam: yeah the whole thing loads into memory. Streaming would fix it.
Me: how long?
Sam: I'd have to look. Maybe a week? Don't hold me to that.
Me: ok. Also it should keep the CSV column order stable, finance complained.
Sam: that's separate, easy though.
Me: right. And we should probably look at whether parquet makes sense later.
Sam: later, yeah."""),
("07","draft","Write an update for the VP. She has 30 seconds.","""INCIDENT LOG (raw):
09:02 alert: p99 latency 4.2s on checkout (normal 180ms)
09:04 oncall ack
09:11 ruled out CDN
09:19 noticed connection pool at ceiling, 200/200
09:31 found: new recommendations service opening a connection per request, not pooling
09:40 rate-limited the recs service at the gateway
09:44 latency back to 210ms
10:15 recs team deployed pooling fix
10:30 rate limit removed, latency 185ms
Revenue impact: checkout conversion dropped from 3.1% to 2.6% for 42 min.
Est. lost orders: ~340. Est. revenue: ~$47k.
The recs service shipped Tuesday. It passed staging because staging has 1/50th the traffic."""),
("08","reply","Reply to this email.","""FROM: dana@acme-partners.com
SUBJECT: Re: integration timeline

Hi - three things before our Thursday call.
1. Can you confirm the sandbox credentials will be ready by the 14th? Our QA
   team has that week blocked.
2. Our legal team is asking whether the data processing addendum covers the
   EU subprocessors you mentioned. Do you have that in writing anywhere?
3. Also - Raj mentioned you might be able to do the migration in one weekend
   rather than two. Is that still on the table?
Thanks, Dana

MY SITUATION (context only, not for the reply):
- sandbox: yes, ready the 11th
- DPA: I genuinely don't know. Need to ask legal. Don't want to promise.
- one weekend: Raj shouldn't have said that. It's two weekends minimum."""),
("09","reply","Reply to this customer.","""FROM: a frustrated customer
SUBJECT: THIRD time this month

This is the third outage this month. We've lost two days of work. Your status
page said "investigating" for four hours with no updates. I'm starting to
wonder whether we picked the wrong vendor. What are you actually doing about this?

WHAT I KNOW:
- outages on the 3rd (90 min), 11th (3 hr), 24th (4 hr) - all three real
- 3rd and 11th: same root cause, a storage driver bug, patched on the 12th
- 24th: unrelated, a bad config push, now gated behind review
- status page delay is a fair hit. We had no owner for it. There is now.
- I can't offer a credit without approval, and I don't have it yet."""),
("10","reply","Reply to this Slack thread.","""THREAD:
Marcus (10:02): heads up, leadership decided we're pausing the API v3 work
  to put everyone on the mobile launch. Effective Monday.
Marcus (10:02): I know this isn't what the team wanted
Jen (10:09): so what happens to the v3 beta customers? we told 6 of them March
Marcus (10:11): good question, I don't have an answer yet

YOU are the v3 tech lead. YOUR VIEW (private):
- You think this is the wrong call. v3 is 3 weeks from beta.
- But it's decided. You're not relitigating it in a public channel.
- Jen's question is the real one and it's yours to answer.
- You do know: 6 customers, 2 have already built against the beta.
- You need a decision from Marcus on what to tell them, by Wednesday."""),
("11","light edit","Light edit only. Fix what makes a reader stumble. Keep my words.","""DRAFT:
Hi team, I wanted to reach out regarding the quarterly review process which
we discussed. As you are aware, we have been experiencing some challenges
with regards to the timeline. The confidence on the delivery date has
decreased somewhat. I think we need to have a conversation about what the
cost difference of achieve the original date would be, versus pushing it.
Let me know your thoughts at your earliest convenience.
Thanks"""),
("12","light edit","Light edit. This is going to a customer tomorrow.","""DRAFT:
Thank you for your patience while we investigated this issue. We have
identified the root cause and deployed a fix. The issue was caused by a
configuration error on our side. We apologize for any inconvenience this
may have caused. Our monitoring shows the system performing better across
the board since the fix. Please do not hesitate to reach out if you have
any further questions or concerns.

NOTE: "better across the board" - actually two of five regions improved,
two are unchanged, one is slightly worse. I wrote that line carelessly."""),
("13","light edit","Light edit this doc section. Don't restructure it.","""DRAFT:
## Rate limits

The API enforces rate limits. Requests are limited to 1000 per hour per API
key. If you exceed this limit you will receive a 429 response. The limit
resets on a rolling window basis. It is important to note that you should
implement exponential backoff in your client. Additionally, bulk endpoints
have a separate limit of 50 requests per hour. Enterprise customers can
request a higher limit by contacting support."""),
("14","review","Review this. Tell me what's wrong with it - I'll do the rewriting myself.","""DRAFT TO REVIEW:
Subject: Q3 Platform Reliability Update

Team,

I'm pleased to share that we've made significant strides in our reliability
posture this quarter. Through concerted cross-functional effort, we've
driven meaningful improvements across several key dimensions.

Uptime reached 99.7%, representing progress toward our target. We've also
reduced mean time to recovery and enhanced our observability tooling.

Looking ahead, we'll continue to prioritize reliability as a core tenet of
our engineering culture. I want to thank everyone for their dedication and
hard work in service of our customers.

More to come."""),
("15","review","Review this for meaning and accuracy. Critique only, no rewrite.","""DRAFT TO REVIEW:
The migration is complete. All 12 services have been moved to the new
cluster and John has signed off on the database layer. Performance is
better than before. We expect no further issues.

The remaining work is documentation, which Sarah will finish by Friday.

SOURCE NOTES (what I actually told the writer):
- 11 of 12 services moved. The billing service is still pending, blocked on
  a vendor firewall rule.
- John reviewed the DB layer and raised two non-blocking concerns.
- p99 improved 20%; p50 is unchanged.
- "no further issues" - nobody said that. I said we have no known blockers.
- Sarah hasn't been asked yet. I suggested her as the likely owner."""),
]
for tid,op,instr,src in tasks:
    (T/f"task-{tid}.md").write_text(f"# Task {tid} — operation: {op}\n\n## Request\n{instr}\n\n## Material\n```\n{src}\n```\n")
print(f"built {len(tasks)} tasks")
for p in sorted(T.glob("*.md")): print(f"  {p.name}  {p.stat().st_size:6d} bytes")
