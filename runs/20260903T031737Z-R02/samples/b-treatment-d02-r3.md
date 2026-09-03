# Make rate-limit key expiry atomic

## Problem

`RateLimiter.check` issued `INCR` and `EXPIRE` as two separate round trips to Redis, with the `EXPIRE` guarded by a check on whether the counter had just been created. If the process died or the connection timed out in the window between those two commands, the key was left in Redis with a value but no TTL. Every subsequent call would see a counter above the limit and reject the request, and because nothing would ever expire the key, the caller stayed locked out until someone deleted it by hand. We hit exactly this in production: roughly 40 users were rate-limited indefinitely and had to be cleared manually from Redis.

## Change

The two commands now go out in a single pipeline, so Redis receives them together and there is no interleaving point at which the key can exist without a TTL. The `EXPIRE` uses `nx=True` rather than the old `count == 1` guard, which preserves the original intent — only set the TTL when the key has none — without depending on the return value of the preceding `INCR`. Since the expiry is now conditioned on the key's actual state rather than on a value read back into Python, the pipeline needs no round trip between the two commands and the failure window closes.

## Tests

Added `test_expiry_survives_crash_between_incr_and_expire`, which simulates a failure after the increment and asserts that the key still carries a TTL, covering the specific sequence that caused the incident.

## Notes for review

The `nx` flag on `EXPIRE` requires Redis 7.0 or later; on older servers the argument is rejected and the call errors rather than silently ignoring the flag. Worth confirming the deployed server version before this ships. Behaviour is otherwise unchanged for callers — the same counter semantics and the same limit comparison — so no migration or backfill is needed for keys already in Redis, though any keys still stuck without a TTL from the incident will need the same manual cleanup as before.