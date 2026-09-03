# Make rate-limit key expiry atomic

The rate limiter issued `INCR` and `EXPIRE` as two separate round trips to Redis, with the `EXPIRE` guarded by a check that the counter had just been created. If the process died or the connection timed out in the gap between those two commands, the key was left incremented but without a TTL, and since only the first increment set the expiry, no subsequent call would ever repair it. The counter then sat at or above the limit forever and the caller was rate-limited indefinitely.

This is not hypothetical: it happened in production, where roughly 40 users were locked out and had to be recovered by deleting their keys from Redis by hand.

The fix issues both commands in a single pipeline, so they reach Redis together and the key cannot exist in an untracked state after a mid-sequence failure. The `count == 1` guard is replaced by `EXPIRE ... NX`, which sets the TTL only when the key has none. That preserves the original intent, a fixed window that starts at the first request rather than sliding on every request, and additionally repairs any key that somehow ends up without a TTL, so a stuck key would now heal itself on the next request instead of persisting.

A regression test covers the crash-between-commands case that produced the incident.

One note for review: pipelining is not the same as atomicity under Redis semantics. The commands are sent as one batch, but without `MULTI` they are not guaranteed to execute without other commands interleaving. That is fine here, since the failure mode being fixed is the client dying between round trips rather than interference from a concurrent client, but it is worth being explicit that this change closes the partial-write window and does not make the increment-and-expire pair transactional.