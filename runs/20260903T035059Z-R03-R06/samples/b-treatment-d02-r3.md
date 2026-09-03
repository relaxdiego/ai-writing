# Make rate-limit key expiry atomic

The rate limiter set a key's TTL in a separate round trip from the increment. `check()` called `INCR`, inspected the result, and only issued `EXPIRE` when the count came back as 1. If the process died or the connection timed out in the gap between those two commands, the key survived with no TTL and never decayed, so the caller was rate-limited until someone deleted the key by hand. This is what happened in the recent production incident: roughly 40 users were locked out indefinitely and had to be cleared manually from Redis.

Both commands now go out in a single pipeline, so a crash can no longer land between them. The `EXPIRE` carries `nx=True`, which preserves the previous behaviour of only setting the TTL on the first increment within a window; without it, every request would push the expiry forward and the window would never close for an active caller. The count is read from the pipeline's first result, and the return condition is unchanged.

One behavioural note for reviewers: the old code branched on `count == 1` to decide whether to set the TTL, whereas the new code always sends `EXPIRE NX` and lets Redis decide. These agree in the normal case, and they also agree in the case that caused the incident, where a key exists without a TTL. The old code would leave such a key untouched forever; the new code repairs it on the next request.

The added test covers the crash window directly, asserting that a key which reaches Redis through `check()` always carries a TTL regardless of where a failure interrupts the call.