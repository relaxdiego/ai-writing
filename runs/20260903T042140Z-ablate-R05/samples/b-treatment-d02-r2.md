# Make rate-limit key expiry atomic

The rate limiter issued `INCR` and `EXPIRE` as two separate round trips to Redis, with the `EXPIRE` guarded by a check that the counter had just been created. If the process died or the connection timed out in the gap between those two calls, the key was left in place with no TTL, and because subsequent calls saw a count greater than one they never attempted to set an expiry again. The counter then climbed past the limit and stayed there, so the caller was rate-limited permanently.

This is not hypothetical: it happened in production, where roughly 40 users were locked out until their keys were deleted from Redis by hand.

The fix pipelines the two commands so they reach Redis together, and sets the TTL with `nx=True` rather than conditioning on the returned count. Using `nx` means the expiry is applied when the key has no TTL and left alone otherwise, which preserves the original window semantics without depending on the counter value to decide whether the key is new. A crash can now happen before the pipeline executes or after, but not between the increment and the expiry.

The new test in `tests/test_ratelimit.py` covers the failure mode directly, asserting that a key always carries a TTL after `check` returns. No change to the public interface or to the behaviour of the limiter under normal operation.