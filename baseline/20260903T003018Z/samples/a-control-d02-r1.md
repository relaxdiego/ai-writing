## Make rate-limit key expiry atomic with the counter increment

### Problem

`RateLimiter.check()` issued `INCR` and `EXPIRE` as two separate round trips:

```python
count = self.redis.incr(key)
if count == 1:
    self.redis.expire(key, self.window)
```

If the process crashed or the connection timed out in the gap between the two commands, the key was left incremented but with no TTL. Since nothing else ever set a TTL on that key (the `count == 1` guard means the expiry is only ever attempted on the first request in a window), the counter stayed above the limit forever and the caller was locked out permanently.

This is not theoretical: in the recent production incident roughly 40 users were rate-limited indefinitely and had to be cleared by hand from Redis.

### Change

Both commands now go out in a single pipeline, and `EXPIRE` uses `NX` so it only applies when the key has no TTL:

```python
pipe = self.redis.pipeline()
pipe.incr(key)
pipe.expire(key, self.window, nx=True)
count, _ = pipe.execute()
return count <= self.limit
```

Two things follow from this:

- The commands are sent together and executed back-to-back by Redis, so there is no longer a window in which a client-side crash can leave `INCR` applied without `EXPIRE`.
- `nx=True` replaces the `count == 1` guard. Instead of "set the TTL on the first request," the rule is now "set the TTL if there isn't one." That is self-healing: any key that has already lost its TTL — including keys stranded by the incident — gets one on the next request rather than staying stuck.

Rate-limiting behavior for the normal path is unchanged: window length, limit, and the `count <= self.limit` decision are all the same. The TTL is still not refreshed on subsequent requests within a window, so this remains a fixed-window limiter, not a sliding one.

### Tests

`test_expiry_survives_crash_between_incr_and_expire` covers the failure mode directly: it exercises the case that previously left a key with no TTL and asserts the key ends up expirable.

### Notes for reviewers

- **`EXPIRE ... NX` requires Redis 7.0+.** Older servers will reject the extra argument. Worth confirming the deployed server version before this ships; if any environment is on 6.x, the alternative is a small Lua script or `SET`-based approach.
- `pipeline()` here is buffered but not wrapped in `MULTI`/`EXEC` unless `transaction=True` (the default in redis-py). If the client is configured with `transaction=False`, the two commands are still sent in one round trip but are not atomic against interleaved commands from other clients — harmless for this specific use, but worth a glance at how the client is constructed.
- Existing stranded keys will clear themselves as those users make their next request; no manual cleanup needed beyond what was already done.