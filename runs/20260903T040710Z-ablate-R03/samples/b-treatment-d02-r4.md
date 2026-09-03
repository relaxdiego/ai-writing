**Fix permanent rate-limit lockout by making INCR and EXPIRE atomic**

The rate limiter set a counter and its TTL in two separate round trips to Redis: `INCR` first, then `EXPIRE` only when the returned count was 1. If the process died or the connection timed out in the gap between those two calls, the key survived with no expiry attached, and since the count never again equalled 1 no later request would set one. The counter then climbed past the limit and stayed there, so the caller was rate-limited for as long as the key existed. This is what happened in production: roughly 40 users were locked out indefinitely and their keys had to be deleted from Redis by hand.

Both commands now go out in a single pipeline, so the client sends them together and a failure between them is no longer possible. The `EXPIRE` carries `nx=True`, which means it sets the TTL only when the key has none, preserving the old behaviour of anchoring the window to the first request in it rather than sliding the window forward on every call. The return value is unchanged, so callers need no modification.

One thing worth noting for review is that this relies on `nx` support in `EXPIRE`, which requires Redis 7.0 or later; on an older server the command will error rather than silently misbehave.

The new test covers the case the old code could not survive, asserting that a key created by `check` carries a TTL immediately rather than only after the second command lands.