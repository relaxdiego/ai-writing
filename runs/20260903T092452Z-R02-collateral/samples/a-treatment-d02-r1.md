# Set the rate-limit TTL atomically with the counter increment

`RateLimiter.check` issued `INCR` and `EXPIRE` as two separate round trips, so any crash, timeout, or dropped connection between them left the counter key with no TTL. The key then persisted forever, its count never reset, and the caller was locked out until someone deleted the key by hand. This happened in production: roughly 40 users were rate-limited indefinitely and had to be cleared manually from Redis.

Both commands now go out in a single pipeline, which redis-py wraps in `MULTI`/`EXEC` by default. The client can no longer die between the increment and the expiry, because there is no longer a point in time at which one has been sent and the other has not. Redis executes the transaction as a unit, so the counter and its TTL are created together or not at all.

The expiry also changes from a conditional issued by the client to `EXPIRE ... NX` evaluated by the server. The old code called `EXPIRE` only when `INCR` returned 1, which is correct only if the count of 1 reliably indicates a fresh key; that assumption is exactly what the incident broke. `NX` instead sets a TTL whenever the key does not already have one, which preserves the intended behaviour (the window starts at the first request and is never extended by later ones) and additionally repairs any key that somehow ended up without a TTL: the next `check` against it will attach one rather than leaving it stuck.

One deployment note for reviewers: the `NX` argument to `EXPIRE` requires Redis 7.0 or later, and older servers will reject the command rather than silently ignoring the flag. Staging and production should be confirmed to be on 7.0+ before this merges.

`tests/test_ratelimit.py` gains `test_expiry_survives_crash_between_incr_and_expire`, covering the failure mode directly: the key must carry a TTL after `check` returns, with no window in which a partially applied write can be observed.