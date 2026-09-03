# Make rate-limit key expiry atomic

## Summary

`RateLimiter.check` issued `INCR` and `EXPIRE` as two separate round trips to Redis, with the `EXPIRE` guarded by a check on whether the counter had just been created. If the process died or the connection timed out in the window between those two calls, the key was left behind with no TTL, and because subsequent calls saw a count greater than 1 they never attempted to set the expiry again — the key persisted forever and the caller was rate-limited indefinitely. This is what happened in production: roughly 40 users were locked out until their keys were cleared from Redis by hand.

This change collapses both commands into a single pipeline, so they are sent together and the counter can no longer exist without a TTL attached. The `count == 1` guard is replaced by `EXPIRE ... NX`, which sets the expiry only when the key has none; that preserves the original intent of not sliding the window forward on every request, while also repairing the state if a key somehow ends up without a TTL. The return value is unchanged, so callers see the same behaviour.

## Testing

Added `test_expiry_survives_crash_between_incr_and_expire`, which covers the failure mode directly: it asserts that a key always carries a TTL after `check` returns, rather than only when the counter was freshly created.

## Notes for reviewers

Pipelining is not a transaction — Redis will still execute the two commands as one batch without interleaving other clients' commands on the same connection, and the `NX` flag means a partial application is self-correcting on the next call rather than permanent. If you would prefer stronger guarantees, the alternative is a Lua script via `EVAL`, which gives true atomicity at the cost of a script cache dependency; that seemed heavier than this bug warrants, but it is worth a look if we add more logic to the window handling later.