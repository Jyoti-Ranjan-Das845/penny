**Production Latency Incident — Resolved**

**Business Impact**
~$47k estimated lost revenue and ~340 lost orders during a 42-minute impact window.

**What Happened**
An alert fired at 09:02 showing p99 latency at 4.2 s against a normal of 180 ms. The new recommendations service, shipped Tuesday, was opening a fresh connection on every request rather than reusing a pool — causing system-wide latency degradation. The incident was resolved at 10:30; latency returned to 185 ms.
