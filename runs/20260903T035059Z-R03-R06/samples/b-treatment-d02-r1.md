# Make rate-limit key expiry atomic

`RateLimiter.check` issued `INCR` and `EXPIRE` as two separate round trips to Redis, with a conditional in between that only set the TTL when the counter came back as 1. If the process died or the connection timed out after the `INCR` landed but before the `EXPIRE` was sent, the key stayed in Redis with no TTL at all. Nothing in the normal path would ever set one afterwards, because the counter was no longer 1, so the key incremented past the limit and stayed there. Every subsequent request from that caller failed the check permanently.

This is what happened in production: roughly 40 users were locked out indefinitely and their keys had to be deleted from Redis by hand before they could make requests again.

The fix pipelines both commands so they are sent in a single round trip, and replaces the `count == 1` guard with `EXPIRE ... NX`, which sets the TTL only when the key has none. The NX flag preserves the original intent — the window starts at the first request and is not extended by later ones — without depending on a return value that a partial failure can invalidate. Since the two commands now travel together, a crash either leaves the key untouched or leaves it incremented with a TTL, and a key that somehow does lack a TTL will acquire one on the next request rather than sticking forever.

One behavioural note for review: `EXPIRE` with `NX` requires Redis 7.0 or later. Older servers reject the flag, so this change raises the minimum server version.

The added test covers the failure mode directly, asserting that a key left behind by an interrupted `check` still ends up with a TTL rather than living forever.