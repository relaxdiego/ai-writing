## Set the rate-limit key's TTL atomically with its counter

`RateLimiter.check` incremented the counter and set its expiry as two separate
round trips to Redis, with the `EXPIRE` conditional on the counter coming back
as 1. If the process died or the second call timed out in the gap between them,
the key survived with no TTL, and since the counter never reset the caller was
rate-limited forever. This is what happened in the recent incident: about 40
users were locked out until their keys were cleared from Redis by hand.

Both commands now go through a pipeline, which redis-py wraps in `MULTI`/`EXEC`
by default, so they are sent in one round trip and applied together. A crash can
now happen before the counter is incremented or after the TTL is set, but not
between the two.

The condition on `count == 1` is replaced by `nx=True` on the `EXPIRE` itself,
which sets a TTL only when the key doesn't already have one. This preserves the
fixed-window behaviour the old code intended, since the TTL is still established
once per window and later increments leave it alone, and it repairs rather than
perpetuates the failure mode: any key that has somehow ended up without a TTL
gets one on its next check instead of hanging around indefinitely. Keys already
stranded in production from the incident have been cleared, but this means a
recurrence would self-heal on the next request rather than needing manual
intervention.

The new test in `tests/test_ratelimit.py` covers the crash window directly,
asserting that the key carries a TTL after `check` returns rather than only that
the return value is correct. The old implementation passes every assertion about
the return value, so the previous suite could not have caught this.

One thing worth knowing for review: the atomicity here rests on redis-py's
pipeline defaulting to `transaction=True`. If this codebase ever moves to a
client or cluster configuration where that default doesn't hold, the guarantee
goes with it, and the fix would need to become a Lua script or a `SET`-with-
expiry formulation instead.