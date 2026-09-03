**Make the rate-limit counter and its TTL atomic**

`check()` now issues INCR and EXPIRE inside a single pipeline, so a key can no longer exist without a TTL.

The old code did INCR, inspected the returned count, and issued EXPIRE only when the count came back as 1. Those were two round trips with application logic between them, and a crash or timeout in the gap left a counter that would never expire. In production this locked out roughly 40 users indefinitely; their keys had to be deleted from Redis by hand before they could make requests again.

The new version sends both commands together and drops the `count == 1` branch, using `EXPIRE ... NX` so the TTL is set on first write and untouched on subsequent increments. That preserves the old semantics of a window that starts at the first request and does not slide, without needing to read the counter to decide.

Two things reviewers should confirm for their deployment. The atomicity comes from redis-py's `pipeline()` defaulting to `transaction=True`, which wraps the commands in MULTI/EXEC; if any caller constructs the client or pipeline with `transaction=False`, the gap reopens. The `NX` flag on EXPIRE also requires Redis 7.0 or later, and will raise on older servers rather than silently ignoring the argument.

The added test covers the failure directly: it simulates the process dying between the two commands and asserts the key still carries a TTL afterwards, which fails against the previous implementation.