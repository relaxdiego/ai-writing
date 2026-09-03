## Fix permanent lockout when rate-limit key loses its TTL

### Background

A production incident left roughly 40 users rate-limited indefinitely. Their Redis counters had to be deleted by hand to restore access.

### Root cause

`RateLimiter.check` issued two separate round trips to Redis:

```python
count = self.redis.incr(key)
if count == 1:
    self.redis.expire(key, self.window)
```

If the process crashed — or the connection timed out — between the `INCR` and the `EXPIRE`, the key was created with no TTL. Since `EXPIRE` was only attempted when `count == 1`, no later call would ever set one: the counter simply kept climbing past the limit forever, and the affected caller was locked out permanently.

### Change

`INCR` and `EXPIRE` are now issued in a single pipeline, so they are sent as one round trip and there is no window in which the key can exist without a TTL:

```python
pipe = self.redis.pipeline()
pipe.incr(key)
pipe.expire(key, self.window, nx=True)
count, _ = pipe.execute()
```

`EXPIRE` uses `nx=True` so it only sets a TTL when the key doesn't already have one. This replaces the `count == 1` guard and preserves the previous behavior of a fixed window that starts at the first request — subsequent requests in the same window do not slide the expiry forward.

### Tests

Added `test_expiry_survives_crash_between_incr_and_expire`, which covers the interrupted-write case that produced the incident: a key that has been incremented must always end up with a TTL, so the limiter self-heals instead of requiring manual cleanup.

### Notes for reviewers

- `EXPIRE ... NX` requires Redis 7.0+ (the `NX`/`XX`/`GT`/`LT` flags were added in 7.0). Worth confirming the deployed server version before merge.
- Existing keys created during the incident window still have no TTL. With `nx=True` they will now receive one on the next `check` call, so they recover on their own; no manual cleanup should be needed this time.
- Behavior under normal operation is unchanged: same limit, same window, same return value.