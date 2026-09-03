## Make rate-limit key expiry atomic

`RateLimiter.check` set the counter and its TTL in two separate round trips: `INCR`, then `EXPIRE` if the returned count was 1. If the process crashed or the connection timed out between those two calls, the key survived with no TTL, and the caller was rate-limited forever.

This happened in production — roughly 40 users were locked out indefinitely and had to be cleared from Redis by hand.

Both commands now go through a single pipeline, with `EXPIRE ... NX` so an existing TTL is never extended by a later request in the same window. There is no longer a window in which a counter can exist without an expiry.

**Behaviour change:** previously the TTL was set only on the first request of a window (`count == 1`); now every request issues an `EXPIRE NX`, which is a no-op when a TTL is already present. Window semantics are unchanged, but a key that somehow lost its TTL will now recover on the next request rather than staying stuck.

Adds `test_expiry_survives_crash_between_incr_and_expire`, which covers the failure mode from the incident.