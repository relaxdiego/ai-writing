## Make rate-limit counter and TTL atomic

`RateLimiter.check` issued `INCR` and `EXPIRE` as two separate round trips, setting the TTL only when the counter came back as 1. If the process crashed or the connection timed out in the gap between the two calls, the key was left with no expiry — the counter stayed above the limit forever and the caller was locked out permanently.

This is what caused the recent production incident: roughly 40 users were rate-limited indefinitely and had to be cleared out of Redis by hand.

Both commands now go through a pipeline, so they're sent together and the key can't survive without a TTL. `EXPIRE` uses `nx=True` so it only sets the TTL when the key doesn't already have one, preserving the old behaviour of not extending the window on every request — previously that was achieved by checking `count == 1`, which is no longer needed since the pipeline issues both commands unconditionally.

Adds a regression test covering the crash-between-`INCR`-and-`EXPIRE` case.

**Note:** `EXPIRE ... NX` requires Redis 7.0+. Worth confirming the deployed version before merging.