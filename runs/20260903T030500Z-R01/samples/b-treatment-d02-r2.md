## Fix rate limiter leaving keys without a TTL

`RateLimiter.check` issued `INCR` and `EXPIRE` as two separate round trips. If the process crashed or the connection timed out between them, the key was left with no expiry — the counter stayed above the limit forever and the caller was locked out permanently.

This happened in production: roughly 40 users were rate-limited indefinitely and had to be cleared out of Redis by hand.

### Change

Both commands now go out in a single pipeline, so the key can never exist without an expiry being set alongside it:

```python
pipe = self.redis.pipeline()
pipe.incr(key)
pipe.expire(key, self.window, nx=True)
count, _ = pipe.execute()
```

`EXPIRE` uses `nx=True` rather than the previous `if count == 1` guard. This preserves the original intent — the TTL is set once, on key creation, and is not extended by subsequent hits within the window — without needing to branch on the counter value.

### Testing

Added `test_expiry_survives_crash_between_incr_and_expire`, which covers the failure mode from the incident: a key that has been incremented always carries a TTL.

### Notes for reviewers

- `EXPIRE ... NX` requires Redis 7.0+.
- Existing TTL-less keys from the incident are not repaired by this change; they were already cleared manually.