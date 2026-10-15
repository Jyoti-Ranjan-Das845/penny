# Task 05 — operation: draft

## Request
Write a Slack message to the engineering channel.

## Material
```
NOTES (mine, messy):
- deploy went out 14:20, rolled back 14:52
- cause: migration 0047 ran twice because the runner retried on a timeout
- 40,000 duplicate rows in `orders_audit`
- restored from 02:00 snapshot, no customer-facing data lost
- Priya spotted it from the latency alert
- fix: idempotency key on migrations, she's got a branch up
- postmortem Thursday, I'll send an invite
```
