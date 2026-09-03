## Fix indefinite lockout when rate-limit keys lose their TTL

### Summary

`RateLimiter.check` issued `INCR` and `EXPIRE` as two separate round trips. If the process crashed or the connection timed out between them, the key was left with no TTL — permanent, and the caller was rate-limited forever.

This bundles both commands into a single pipelined transaction so the key can never exist without an expiry.

### Background

Found after a production incident: roughly 40 users were rate-limited indefinitely and had to be cleared out of Redis by hand.

The old code only set the TTL when `INCR` returned `1`, i.e. on the first request in a window. That single moment is the whole exposure window — but it's also the moment a cold-start or a Redis timeout is most likely to interrupt. Once the TTL was missed, nothing in the code path ever set it again: every subsequent `check` incremented a key that was already over the limit and returned `False` forever.

### Change

```python
pipe = self.redis.pipeline()
pipe.incr(key)
pipe.expire(key, self.window, nx=True)
count, _ = pipe.execute()
return count <= self.limit
```

Two things to note:

- **`nx=True`** replaces the `if count == 1` guard. The TTL is set only when the key doesn't already have one, so we don't slide the window forward on every request the way an unconditional `EXPIRE` would.
- **The pipeline is a transaction.** redis-py wraps pipelines in `MULTI`/`EXEC` by default (`transaction=True`), so both commands are applied together or not at all. This is load-bearing — constructing the pipeline with `transaction=False` would reintroduce the bug in a subtler form.

### Testing

Added `test_expiry_survives_crash_between_incr_and_expire`, which reproduces the incident: it simulates a failure after `INCR` and asserts the key either doesn't exist or carries a TTL — never a bare key with `TTL == -1`.

### Compatibility

`EXPIRE ... NX` requires **Redis 7.0+** and a redis-py version that forwards the flag (4.x+). Worth confirming the deployed server version before merging; on an older Redis the `nx` argument will raise rather than fail silently, so this would surface immediately in staging rather than in production.

### Remediation

This fixes the cause but not existing damage. Any keys already stranded without a TTL will stay stranded, since `nx=True` will now happily set a TTL on them the next time they're touched — meaning affected users self-heal after one more request, but only once the window elapses. If any of the ~40 keys from the incident are still live, a one-off sweep for rate-limit keys with `TTL == -1` is worth running alongside the deploy.