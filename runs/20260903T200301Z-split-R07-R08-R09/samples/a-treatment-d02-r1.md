**Make the rate-limit window atomic so a crash can't strand a key without a TTL**

`RateLimiter.check` issued INCR and EXPIRE as two separate round trips, and set the TTL only when the counter came back as 1. If the process died or the call timed out in the gap between them, the key survived at count 1 with no expiry, and every later request for that key incremented a counter that would never reset. The caller was locked out until someone deleted the key by hand. This happened in production: roughly 40 users were rate-limited indefinitely and had to be cleared from Redis manually.

Both commands now go out in a single pipeline, so the key is never left in a half-initialised state. The EXPIRE carries `nx=True` so it applies only when the key has no TTL, which preserves the previous behaviour of anchoring the window to the first request rather than sliding it forward on every check. The limit comparison is unchanged, and so is the interface: `check` still takes a key and returns a bool.

One deployment note. `EXPIRE ... NX` needs Redis 7.0 or later, and the `nx` keyword needs a redis-py that passes it through. On an older server the command fails rather than silently ignoring the flag, so the Redis version wants confirming before this ships.

The new test in `tests/test_ratelimit.py` covers the failure directly: it drives a counter through the crash point between the increment and the expiry and asserts the key still carries a TTL afterwards. Under the old implementation it fails.