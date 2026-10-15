**Subject: Checkout latency incident — resolved, ~$47k impact**

Checkout p99 latency hit 4.2s this morning (normal 180ms). On-call throttled the cause at 9:40 and latency was back to 210ms by 9:44. The permanent fix shipped at 10:15; we're at 185ms now. Total degradation: 42 minutes.

**Impact:** checkout conversion fell from 3.1% to 2.6%. Roughly 340 lost orders, about $47k — both estimates.

**Cause:** the newly released recommendations service opened a database connection per request instead of pooling, and exhausted checkout's 200-connection pool.

**Why we didn't catch it:** staging carries 1/50th of production traffic, so the service passed there. A connection-per-request bug is effectively invisible at that volume — this would have escaped review again. Closing that gap is the real work here, and I'll come back with options rather than guess at them now.