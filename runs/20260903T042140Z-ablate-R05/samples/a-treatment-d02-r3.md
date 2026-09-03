**Make rate-limit key expiry atomic with the counter increment**

`RateLimiter.check` used to issue INCR and EXPIRE as two separate round trips, setting the TTL only on the first increment. If the process died or the connection timed out in the gap between them, the counter key was left with no expiry, so it accumulated forever and the caller was locked out until someone deleted the key by hand. We hit exactly this in production: roughly 40 users were rate-limited indefinitely and had to be cleared manually from Redis.

Both commands now go out in a single pipeline, which under redis-py's default transactional pipeline means they are sent together and applied as a unit, closing the window the incident fell through. The TTL condition also moves from the application to Redis: instead of setting the expiry when the returned count is 1, we issue `EXPIRE ... NX`, which sets it only when the key has no TTL. The behaviour on a fresh key is the same, and as a side benefit any key that somehow ends up without a TTL will have one set on the next call rather than living forever.

One thing worth checking before this merges: the `NX` flag on EXPIRE requires Redis 7.0 or later. Our staging and production clusters are on 7.2, but anyone running an older Redis locally or in CI will see an error from `pipe.execute()`, so it may be worth pinning the version in the dev compose file if it is not already.

The new test in `tests/test_ratelimit.py` covers the failure directly, simulating a crash between the increment and the expiry and asserting that the key still carries a TTL afterward.