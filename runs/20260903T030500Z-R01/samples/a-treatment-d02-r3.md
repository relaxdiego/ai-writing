## Make rate-limit counter expiry atomic

`RateLimiter.check` issued `INCR` and `EXPIRE` as two separate round trips. If the process crashed or timed out between them, the key was left with no TTL — the counter never reset and the caller was rate-limited indefinitely.

This happened in production: roughly 40 users were locked out and their keys had to be deleted from Redis by hand.

### Change

Both commands now go out in a single pipeline, so the key can never exist without a TTL:

```python
pipe = self.redis.pipeline()
pipe.incr(key)
pipe.expire(key, self.window, nx=True)
count, _ = pipe.execute()
```

`nx=True` replaces the old `if count == 1` guard: `EXPIRE` only sets a TTL when the key doesn't already have one, so the window still starts at the first request and isn't extended by later ones. That check is now Redis-side rather than a decision made between round trips.

### Tests

Adds `test_expiry_survives_crash_between_incr_and_expire`, covering the failure the incident exposed.

### Notes for reviewers

- Requires redis-py 3.x or later for the `nx` keyword on `expire`.
- Existing keys that are already stuck without a TTL are not repaired by this change — they still need to be cleared manually if any remain.