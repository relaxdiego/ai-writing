## Fix rate limiter leaving keys without a TTL

`RateLimiter.check` issued `INCR` and `EXPIRE` as two separate round trips. If the process crashed or timed out between them, the key was left with no TTL and never expired — the caller stayed rate-limited forever.

This caused a production incident in which roughly 40 users were locked out indefinitely and had to be cleared manually from Redis.

### Change

Both commands are now sent in a single pipeline, and `EXPIRE` uses `nx=True` so it only sets a TTL when the key doesn't already have one. This replaces the previous `count == 1` check, which was the thing that could be skipped by an ill-timed crash.

### Notes

A pipeline is not a transaction: Redis can still fail between the two commands within it. What it removes is the window where the client is responsible for issuing the second command — a crash on our side after `INCR` no longer leaves an immortal key. Closing the remaining gap entirely would need a Lua script or `SET`-with-expiry semantics; that's a larger change and not what the incident called for.

`nx=True` requires Redis 7.0+.

### Tests

Added `test_expiry_survives_crash_between_incr_and_expire`, covering the failure mode from the incident.