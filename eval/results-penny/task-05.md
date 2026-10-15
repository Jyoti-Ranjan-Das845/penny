Heads up on today's deploy: it went out at 14:20 and we rolled it back at 14:52.

Migration 0047 ran twice — the runner retried after a timeout — which left about 40,000 duplicate rows in `orders_audit`. We restored from the 02:00 snapshot, so no customer-facing data was lost. Priya caught it off the latency alert.

Fix is an idempotency key on migrations so a retry can't re-run one. Priya has a branch up if you want to take a look.

Postmortem Thursday, I'll send an invite.