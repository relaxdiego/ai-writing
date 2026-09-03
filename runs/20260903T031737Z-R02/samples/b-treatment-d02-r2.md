# Make rate-limit key expiry atomic

## Summary

`RateLimiter.check` incremented the counter and set its TTL as two separate Redis round trips, with the `EXPIRE` guarded by a `count == 1` check. If the process died or the connection timed out in the gap between those two commands, the key survived with no TTL at all, and because it was already past 1 no later call would ever set one. The counter then climbed monotonically forever and the caller was rate-limited permanently. This change collapses both commands into a single pipeline and replaces the `count == 1` guard with `EXPIRE ... NX`, so the TTL is established in the same round trip as the increment and the "only set on first hit" semantics are enforced by Redis rather than by application-side state.

## Motivation

A production incident left roughly 40 users rate-limited indefinitely; recovery required deleting their keys from Redis by hand. The window for this is small but it is hit every time a worker is killed mid-request, and the damage does not decay on its own, so occurrences accumulate until someone notices and intervenes.

## Notes for reviewers

The `NX` flag is doing the work that `count == 1` used to do, and it is strictly stronger: `count == 1` could be true on a key that already had a TTL (after an expiry race between two callers), which would push the window out, whereas `NX` refuses to touch an existing TTL. `EXPIRE` with `NX` requires Redis 7.0 or later — worth confirming against the deployed version before merge. Pipelining here is not transactional in the `MULTI` sense, but both commands are written to the socket together, which removes the application-side gap that caused the incident; a crash now loses both commands or neither.

## Testing

Added `test_expiry_survives_crash_between_incr_and_expire`, which asserts the key carries a TTL after a single `check` call rather than depending on a follow-up call to repair it.