## Fix permanent rate-limit lockout by making INCR + EXPIRE atomic

### Summary

`RateLimiter.check()` issued `INCR` and `EXPIRE` as two separate round trips to Redis. If the process crashed or the connection timed out in the window between them, the counter key was left with no TTL — meaning it never reset and the caller was rate-limited forever.

This change collapses both commands into a single pipelined round trip and uses `EXPIRE ... NX` so the TTL is set only when the key has none.

### Background

This was found after a production incident in which roughly 40 users were rate-limited indefinitely. Recovery required manually deleting the orphaned keys from Redis. The old code path:

```python
count = self.redis.incr(key)
if count == 1:
    self.redis.expire(key, self.window)   # <-- never runs if we die here
return count <= self.limit
```

Any failure after `INCR` and before `EXPIRE` produced a persistent key. Once that happened, every subsequent request incremented the same key with no expiry, so the counter only ever grew past the limit.

### Changes

**`src/api/ratelimit.py`**
- `check()` now builds a pipeline, queues `INCR` and `EXPIRE`, and executes them together, so both commands are sent in one round trip.
- The TTL is applied with `nx=True` instead of being conditioned on `count == 1`. This is equivalent for the normal path (a fresh key has no TTL, so `NX` sets it) but is also self-healing: a key that somehow lost its TTL gets one on the next request rather than staying orphaned.

**`tests/test_ratelimit.py`**
- Added `test_expiry_survives_crash_between_incr_and_expire`, which covers the failure mode from the incident: after a simulated interruption, the key must still carry a TTL and the caller must eventually be allowed through again.

### Notes on correctness

- **Atomicity caveat:** a pipeline is one round trip, not a transaction. Redis will not interleave another client's commands *between* the two in a way that matters here, and — critically — the client can no longer die between sending them. If stricter guarantees are wanted later, `MULTI/EXEC` or a Lua script would be the next step; pipelining is sufficient for the observed failure mode.
- **Behavior change:** the TTL is no longer refreshed-on-first-hit-only in terms of application logic but delegated to Redis via `NX`. Window semantics are unchanged — this remains a fixed window, not a sliding one.
- **`EXPIRE ... NX` requires Redis 7.0+.** Worth confirming the deployed server version before merge; on older servers the `nx` argument will error rather than silently no-op.

### Risk

Low. The change is confined to a single method, the happy path is behaviorally identical, and the failure path strictly improves. Rollback is a straight revert — though doing so reintroduces the incident's root cause.