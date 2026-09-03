## Set the rate-limit key's TTL atomically with its increment

`RateLimiter.check` incremented the counter key and then set its expiry as two separate round trips to Redis, with the `EXPIRE` guarded by `count == 1`. If the process died or the connection timed out in the gap between the two calls, the key survived with no TTL and no subsequent call would ever set one — the `count == 1` guard had already been passed and would never be true again for that key. The counter then climbed past the limit and stayed there, so the caller was rate-limited for good. Last week's incident was exactly this: roughly 40 users were locked out indefinitely and had to be cleared by hand from Redis before they could make requests again.

This change moves both commands into a single pipeline, so they travel as one round trip and execute as one transaction — there is no longer a window in which the increment can land without its expiry. The `EXPIRE` also carries `nx=True` rather than being gated on the counter's value, which preserves the fixed-window behaviour (the TTL is set on the first increment and not extended by later ones) while making the code self-healing: a key that somehow ends up without a TTL gets one on the next `check` instead of persisting forever.

### Deployment note

`EXPIRE` with the `NX` flag requires Redis 7.0 or later. Our production and staging clusters are on 7.2, but anything running an older server will see an error from the pipeline rather than the previous silent behaviour, so local development environments pinned to Redis 6 will need to be upgraded.

### Testing

Added `test_expiry_survives_crash_between_incr_and_expire`, which simulates a failure between the increment and the expiry and asserts that the key either carries a TTL or is absent entirely — never present-and-permanent. The existing window and limit tests cover the unchanged counting semantics.