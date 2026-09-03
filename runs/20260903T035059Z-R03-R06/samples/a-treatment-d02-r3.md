**Set the rate-limit TTL in the same round trip as the counter increment**

`RateLimiter.check` issued `INCR` and `EXPIRE` as two separate calls, with the `EXPIRE` guarded by `count == 1`. If the process died or the connection timed out in the gap between them, the key was left at 1 with no TTL, and because the guard only fires on the first increment, nothing afterwards would ever set one. The key then counted up forever and the caller was locked out permanently. This is what happened in production: roughly 40 users were stuck behind a rate limit that could not expire, and the keys had to be deleted from Redis by hand.

Both commands now go out in a single pipeline, which redis-py wraps in `MULTI`/`EXEC` by default, so the server applies them together or not at all. A crash mid-flight now leaves either no increment or an increment with a TTL attached, and neither state strands the caller.

The `EXPIRE` carries `nx=True` in place of the old `count == 1` guard. That preserves the existing window semantics, since the TTL is set only when the key has none, meaning a window still starts at the first request and is not extended by later ones. It also repairs the failure mode rather than merely avoiding it: a key that somehow has no TTL, including one left over from the incident, gets one on its next request instead of persisting until someone notices.

Note that `EXPIRE ... NX` requires Redis 7.0 or later on the server and redis-py 4.x on the client. Older servers reject the option outright, so this will fail loudly rather than silently skipping the expiry, but the deployment does need to be on 7.x before this merges.

The new test covers the crash window directly, asserting that a key observed after an interrupted `check` still carries a TTL.