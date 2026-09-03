# Make rate limit key expiry atomic

## Summary

`RateLimiter.check` issued `INCR` and `EXPIRE` as two separate round trips to Redis, with the `EXPIRE` guarded by a check on whether the returned count was 1. If the process died or the connection timed out in the gap between those two calls, the key was left incremented but with no TTL, so it never decayed and the caller stayed over the limit forever. This change collapses both commands into a single pipeline and sets the TTL with `nx=True`, which means the expiry is applied only when the key has none — preserving the old "set the window on first hit" semantics without depending on the returned count, and without a window in which the key can exist untimed.

## Motivation

We hit this in production: roughly 40 users were rate-limited indefinitely and had to be unblocked by deleting their keys from Redis by hand. The failure is silent from the application's point of view, since `check` returns a correct answer for the request that crashed and only the *next* requests see a key that can never fall back under the limit. Nothing in the metrics distinguished a permanently stuck key from a user legitimately hammering the endpoint, which is why it took an incident to surface.

## Notes for reviewers

The switch from `count == 1` to `nx=True` is the substantive part and worth a careful look. The old form re-armed the TTL only on the first increment within a window; `nx=True` re-arms whenever the key has no TTL, which is the same thing in the normal path but additionally repairs any key already stranded by the old bug. Existing stuck keys in production will therefore heal themselves on the affected user's next request rather than needing another manual sweep. The pipeline is not transactional in the `MULTI`/`EXEC` sense, but both commands are sent in one round trip, so there is no longer a point at which the client can die between them.

## Testing

Added `test_expiry_survives_crash_between_incr_and_expire`, which asserts that a key always carries a TTL after `check` returns, covering the interleaving that produced the incident.