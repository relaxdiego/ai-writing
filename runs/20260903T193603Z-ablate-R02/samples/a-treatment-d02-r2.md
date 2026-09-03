## Make the rate-limit window atomic

`RateLimiter.check` issued INCR and EXPIRE as two separate round trips to Redis. If the process died or the connection timed out between them, the counter key was left with no TTL, so it never decayed and the caller was rate-limited forever. That happened in production: roughly 40 users were locked out indefinitely and had to be cleared by hand from Redis.

The two commands now go out in a single pipeline, so a failure takes both or neither. The TTL is set with `nx=True` rather than gated on `count == 1`, which preserves the old semantics (the window is fixed from the first request in it and is not extended by later ones) without depending on the counter value to decide whether the expiry has already been set. It also self-heals: a key that has somehow lost its TTL gets one on the next request through, instead of staying stuck until someone deletes it manually.

Note that pipelining here is not the same as a transaction. Redis executes a pipeline's commands in order without interleaving other clients' commands into it, and the client sends them as one write, so the failure mode that caused the incident is gone. If a stronger guarantee is wanted later, the natural next step is a Lua script, but that is a larger change than this incident calls for.

`EXPIRE ... NX` requires Redis 7.0 or newer and redis-py 4.x. Both are satisfied in staging and production; anyone running an older Redis locally will see an error from `pipe.execute()` rather than a silent fallback.

The new test covers the crash window directly: it simulates the process dying after INCR and before EXPIRE and asserts the key still carries a TTL, which is the exact state that produced the permanent lockout.