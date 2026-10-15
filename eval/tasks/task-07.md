# Task 07 — operation: draft

## Request
Write an update for the VP. She has 30 seconds.

## Material
```
INCIDENT LOG (raw):
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
The recs service shipped Tuesday. It passed staging because staging has 1/50th the traffic.
```
