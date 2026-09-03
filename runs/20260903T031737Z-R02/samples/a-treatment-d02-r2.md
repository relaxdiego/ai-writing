## Make rate-limit key expiry atomic with the increment

`RateLimiter.check` issued `INCR` and `EXPIRE` as two separate round trips, setting the TTL only when the returned count was 1. If the process crashed or the connection timed out in the gap between those two calls, the key survived with no expiry attached, and since the count never reset the caller was rate-limited forever. We hit this in production: roughly 40 users were locked out indefinitely and had to be cleared by hand from Redis.

This change moves both commands into a single pipeline so they are sent together and the TTL can no longer be orphaned by a failure in between. `EXPIRE` now runs with `NX`, which sets the TTL only when the key has none, so it is safe to issue on every call rather than just the first — the window still starts at the first increment and is not extended by subsequent requests, matching the previous semantics. The count-is-1 check is gone because it existed only to decide whether to make the second round trip, and `NX` makes that decision server-side.

One consequence worth noting: `EXPIRE ... NX` requires Redis 7.0 or later and redis-py 4.2+. Both are satisfied in our environments, but a rollback of the Redis version below 7.0 would surface as an error from `pipe.execute()` rather than a silent fallback.

The added test covers the failure mode directly — it asserts that a key still carries a TTL when the process dies between the increment and the expiry, which the old two-call implementation could not guarantee.