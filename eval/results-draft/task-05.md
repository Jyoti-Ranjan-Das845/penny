@engineering — deploy incident today, now resolved. Details below.

Deploy went out at 14:20 and was rolled back at 14:52. Root cause: migration `0047` ran twice because the runner retried on a timeout.

Priya spotted the issue from the latency alert. Impact was 40,000 duplicate rows in `orders_audit`; we restored from the 02:00 snapshot. No customer-facing data was lost.

Fix is an idempotency key on migrations — Priya has a branch up. Postmortem is Thursday; I'll send a calendar invite.
