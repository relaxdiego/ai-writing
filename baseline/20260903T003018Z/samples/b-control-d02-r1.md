# Make rate-limit INCR + EXPIRE atomic

## Summary

`RateLimiter.check()` issued `INCR` and `EXPIRE` as two separate round trips. If the process crashed or the connection timed out in the window between them, the key was left with no TTL — permanently. Every subsequent request for that key incremented a counter that would never reset, locking the caller out forever.

This change batches both commands into a single Redis pipeline (`MULTI`/`EXEC`), so the key either gets created with a TTL or isn't created at all.

## Background

We hit this in production: roughly 40 users ended up rate-limited indefinitely and had to be cleared out of Redis by hand. The trigger was a crash between the two commands; the symptom was a counter above the limit with `TTL == -1`.

## Changes

**`src/api/ratelimit.py`**
- `check()` now uses a pipeline: `INCR` and `EXPIRE` are submitted together and executed atomically.
- `EXPIRE` now uses `nx=True` (set TTL only if the key has none) instead of being guarded by the `count == 1` check. This preserves the original intent — the TTL is anchored to the first request in a window and not refreshed by later ones — while no longer depending on the process staying alive between two round trips.

**`tests/test_ratelimit.py`**
- Added `test_expiry_survives_crash_between_incr_and_expire`, which asserts the key always carries a TTL after `check()`, covering the exact interleaving that caused the incident.

## Behavior notes

- Steady-state behavior is unchanged: first request in a window sets the TTL, subsequent requests do not extend it, and the limit comparison is identical.
- One round trip instead of two (the pipeline is a single network exchange), so this is marginally faster under load.
- Keys already stranded without a TTL by the old code are *not* healed by this change — `nx=True` only applies when the key is missing a TTL, so those keys will in fact pick one up on their next `check()`. Any keys already above the limit will still be rejected until that TTL elapses; if we want them cleared immediately, that's a separate one-off Redis cleanup.

## Compatibility

`EXPIRE ... NX` requires Redis 7.0+ and a redis-py version that forwards the `nx` keyword (4.x+). Worth confirming the deployed Redis version before merge — on an older server this raises rather than silently degrading, so it would fail loudly in staging.

## Testing

- New regression test simulating a failure between the increment and the expiry.
- Existing rate-limit tests pass unchanged.