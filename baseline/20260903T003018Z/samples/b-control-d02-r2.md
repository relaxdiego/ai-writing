# Fix permanent rate-limit lockout by making INCR + EXPIRE atomic

## Problem

`RateLimiter.check()` issued `INCR` and `EXPIRE` as two separate Redis round trips:

```python
count = self.redis.incr(key)
if count == 1:
    self.redis.expire(key, self.window)
return count <= self.limit
```

If the process crashed or the connection timed out between those two calls, the key existed with a counter but **no TTL**. Since the `EXPIRE` was guarded by `count == 1`, no subsequent request would ever set one — the key incremented forever and the caller was rate-limited permanently.

This happened in production: roughly 40 users were locked out indefinitely and had to be cleared manually from Redis.

## Change

`check()` now issues both commands in a single pipeline:

```python
pipe = self.redis.pipeline()
pipe.incr(key)
pipe.expire(key, self.window, nx=True)
count, _ = pipe.execute()
return count <= self.limit
```

Both commands are sent and executed together, so there is no window in which the key can exist without a TTL. The `nx=True` flag means `EXPIRE` only applies when the key has no TTL, which preserves the original semantics: the window starts at the first request and is not extended by subsequent ones. This also lets us drop the `count == 1` guard, which was the thing that made the missing-TTL state unrecoverable.

## Testing

Added `test_expiry_survives_crash_between_incr_and_expire`, which covers the failure mode directly: after a simulated interruption at the point that previously lost the TTL, the key still carries an expiry and the caller recovers once the window elapses.

## Notes for reviewers

- **Behavior is unchanged on the happy path** — same counter, same window, same limit comparison.
- **`nx` on `EXPIRE` requires Redis 7.0+.** Worth confirming the deployed version before merge; on older servers the flag is rejected.
- **Existing keys without a TTL are not repaired by this change.** It prevents new occurrences, but any keys still stuck from the incident need the manual clear (a one-off scan for rate-limit keys with `TTL == -1` would cover it).
- Pipelining here is not a Lua/`MULTI` transaction — it batches the round trip rather than guaranteeing isolation. That is sufficient for this bug, since the risk was losing the second command entirely, not interleaving with another client.