# Make rate-limit key expiry atomic

The rate limiter issued `INCR` and `EXPIRE` as two separate round trips to Redis, with the `EXPIRE` guarded by a check that the counter had just been created. If the process died or the connection timed out in the gap between the two commands, the key was left incremented but without a TTL, and since the guard only fires when the count is exactly 1, no later call would ever set one. The key then sat in Redis forever, and every subsequent request from that caller counted against a limit that could no longer reset, locking them out permanently.

This is not hypothetical: we hit it in production, where roughly 40 users were rate-limited indefinitely and had to be unblocked by deleting their keys from Redis by hand.

The fix sends both commands in a single pipeline, so they reach Redis together and the crash window between them disappears. The `count == 1` guard is replaced by `EXPIRE ... NX`, which sets the TTL only when the key has none, giving the same "don't extend the window on every hit" behaviour without depending on the counter's value to decide. That distinction matters here, because a key that somehow ends up without a TTL will now acquire one on the next call rather than staying stuck.

Behaviour is otherwise unchanged: the same counter, the same window, the same return value. A regression test covers the crash-between-`INCR`-and-`EXPIRE` case that produced the incident.

One caveat for reviewers: `EXPIRE` with `NX` requires Redis 7.0 or later. Worth confirming the deployed version before this ships.