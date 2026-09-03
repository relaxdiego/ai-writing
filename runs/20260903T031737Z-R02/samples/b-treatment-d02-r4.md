# Make rate-limit key expiry atomic

## Summary

`RateLimiter.check` incremented the counter and set its TTL as two separate Redis round trips, with the `EXPIRE` guarded by a `count == 1` check on the client side. If the process died or the connection timed out in the gap between those two commands, the key survived with no TTL at all — and since the counter was already past 1, no later call would ever set one. The key stayed above the limit forever and the caller was locked out until someone deleted it by hand. That is what happened in production: roughly 40 users were rate-limited indefinitely and had to be cleared manually from Redis.

This change collapses both commands into a single pipeline so they travel as one round trip, and moves the "only set the TTL once" logic from the client into Redis itself via `EXPIRE ... NX`. The `NX` flag sets the expiry only when the key has none, which preserves the original intent — a fixed window starting at the first request, not a sliding one refreshed by every hit — while removing the client-side `count == 1` branch that was the source of the fragility. Behaviour for callers is unchanged; the window length, the limit comparison, and the return value are all the same.

## Notes for reviewers

The pipeline is not a transaction, so a crash mid-pipeline is still theoretically possible, but the failure window shrinks from "between two application-level round trips" to "between two commands in one buffer", and the `NX` semantics mean a subsequent `check` on a TTL-less key will now repair it rather than skip the `EXPIRE` forever. That self-healing property is the part that actually fixes the incident class; the pipeline is what makes the window small enough to stop mattering in practice.

`EXPIRE` with `NX` requires Redis 7.0 or later, which our deployed version satisfies — worth confirming against any environment that pins an older server.

## Testing

Added `test_expiry_survives_crash_between_incr_and_expire`, which exercises the case the old code could not survive: a key that already exists without a TTL must come out of `check` with one set.