## Make rate-limit counter TTL crash-safe

### Problem

`RateLimiter.check()` issued `INCR` and `EXPIRE` as two separate round trips, with the `EXPIRE` guarded by `count == 1`:

```python
count = self.redis.incr(key)
if count == 1:
    self.redis.expire(key, self.window)
```

If the process crashed or the connection timed out in the window between those two calls, the key was left at `1` with no TTL. Nothing else in the code path ever set one — the `count == 1` guard means subsequent requests skip `EXPIRE` entirely — so the key incremented forever and the caller was locked out permanently.

This is not hypothetical: in a recent production incident roughly 40 users were rate-limited indefinitely and had to be cleared out of Redis by hand.

### Change

Both commands are now sent in a single transactional pipeline:

```python
pipe = self.redis.pipeline()
pipe.incr(key)
pipe.expire(key, self.window, nx=True)
count, _ = pipe.execute()
```

Two things fix the bug:

1. **Atomicity.** redis-py's pipeline defaults to `transaction=True`, so the two commands are wrapped in `MULTI`/`EXEC` and Redis executes them as a unit. There is no longer an interleaving point where the key exists without a TTL.
2. **Self-healing.** `EXPIRE ... NX` is now attempted on every call instead of only on the first increment. `NX` means "only set a TTL if the key has none," so the steady-state behavior is unchanged (the window is not extended by later requests within it), but any key that somehow ends up TTL-less — including keys stranded by the old code before this deploy — gets one on the next request.

### Behavior notes

- Window semantics are unchanged: the TTL is still anchored to the first request in a window, not sliding.
- Rate-limit decisions are unchanged; `count <= self.limit` is evaluated against the same value.
- One fewer round trip in the common (first-request) case, one more in the steady-state case, though all are now batched into a single `execute()`.

### Compatibility

`EXPIRE` gained the `NX` flag in **Redis 7.0**, and the `nx=` keyword requires **redis-py 4.x+**. Against an older server this will raise an error rather than silently ignoring the flag. Worth confirming the deployed Redis version before merge if any environment is still on 6.x.

### Testing

Adds `test_expiry_survives_crash_between_incr_and_expire`, which asserts the key carries a TTL after a failure injected between the two commands — the exact sequence that produced the incident.

### Rollout

Existing stranded keys will be repaired automatically the next time the affected key is touched, so no migration or manual Redis cleanup is required. If any users are currently locked out, they will be released on their next request rather than needing to wait for a manual clear.