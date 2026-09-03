## Fix permanent lockout when rate-limit keys lose their TTL

### Summary

`RateLimiter.check()` issued `INCR` and `EXPIRE` as two separate round trips. If the process crashed, timed out, or lost its connection between the two, the key was left in Redis with no TTL — permanently over the limit, permanently locking out that caller.

This replaces the two calls with a single pipelined (MULTI/EXEC) transaction, and sets the TTL with `NX` so it's only applied when the key has no expiry.

```python
pipe = self.redis.pipeline()
pipe.incr(key)
pipe.expire(key, self.window, nx=True)
count, _ = pipe.execute()
return count <= self.limit
```

### Motivation

Found after a production incident: roughly 40 users were rate-limited indefinitely and had to be cleared out of Redis by hand. The window for the bug is small but it's hit continuously under real traffic, so it recurred.

### Why this fixes it

- **Atomicity** — the commands are sent as one transaction, so `EXPIRE` can't be orphaned by a crash between round trips. Either both apply or neither does.
- **`nx=True` instead of `count == 1`** — the old code only set the TTL when it believed it had created the key. That check was both fragile (a lost `EXPIRE` was never retried on subsequent calls) and reliant on client-side state. `NX` moves the decision to Redis: set a TTL if and only if the key doesn't already have one. A key that somehow ends up without a TTL now self-heals on the next request rather than staying stuck forever.

Behavior is otherwise unchanged: same window, same limit, same return value. The window still starts at the first request and is not extended by subsequent ones.

### Testing

Added `test_expiry_survives_crash_between_incr_and_expire`, which asserts the key carries a TTL after a simulated failure at the point that previously produced the orphaned key. Existing rate-limit tests pass unchanged.

### Notes for reviewers

- `EXPIRE ... NX` requires **Redis 7.0+**; please confirm the deployed server version before merging. If any environment is on 6.x, this needs to become a Lua script or a `SET`-based approach instead.
- One extra round trip is saved in the common case (pipelined rather than two sequential calls).
- Consider a one-off sweep for existing TTL-less keys matching the rate-limit prefix — this change prevents new occurrences but does not clean up any keys still stranded from the incident.