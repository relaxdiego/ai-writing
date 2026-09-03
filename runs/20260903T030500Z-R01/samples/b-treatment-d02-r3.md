**Fix rate limiter leaving keys without a TTL**

`RateLimiter.check` issued `INCR` and `EXPIRE` as two separate round trips. If the process crashed or timed out between them, the key was left with no expiry — permanently counted against the caller with no way to recover except manual deletion in Redis.

This surfaced in production: roughly 40 users were rate-limited indefinitely and had to be cleared by hand.

**Change:** both commands are now sent in a single pipeline, so they reach Redis together rather than as two independently-failable calls. `EXPIRE` uses `nx=True`, which sets the TTL only if the key doesn't already have one — this replaces the old `if count == 1` guard and preserves the fixed-window behaviour (the window starts at the first request and isn't extended by subsequent ones).

**Tests:** added `test_expiry_survives_crash_between_incr_and_expire`, covering the failure mode directly.

Note that a pipeline is not atomic — it batches round trips but does not guarantee both commands execute. The remaining exposure is a Redis-side failure between the two commands within the batch, which is far narrower than a client crash or network timeout. A Lua script or `MULTI`/`EXEC` would close it entirely; that seemed disproportionate for this fix, but worth flagging if reviewers disagree.