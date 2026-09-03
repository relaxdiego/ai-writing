## Fix rate limiter leaving keys without a TTL

`RateLimiter.check` issued `INCR` and `EXPIRE` as two separate round trips. If the process crashed or timed out between them, the key was left with no TTL — the counter stayed above the limit forever and the caller was locked out permanently.

This is what caused the recent production incident: roughly 40 users were rate-limited indefinitely and had to be cleared out of Redis by hand.

### Change

Both commands now go out in a single pipeline, so the key can never exist without an expiry:

```python
pipe = self.redis.pipeline()
pipe.incr(key)
pipe.expire(key, self.window, nx=True)
count, _ = pipe.execute()
```

`EXPIRE` uses `nx=True` so it only sets a TTL when the key doesn't already have one. This replaces the old `if count == 1` guard and is more robust: the previous version skipped `EXPIRE` on every call after the first, so a key that somehow lost its TTL never got one back.

### Testing

Added `test_expiry_survives_crash_between_incr_and_expire`, covering the failure mode from the incident.

### Notes for reviewers

- `nx` on `EXPIRE` requires Redis 7.0+.
- This does not repair keys already stranded without a TTL; those were cleared manually during the incident.