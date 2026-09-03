**Fix permanent lockout when rate-limit key loses its TTL**

The rate limiter incremented a counter and set its expiry as two separate Redis round trips. If the process crashed or the connection timed out in the gap between them, the key survived with no TTL, so its count never reset and the caller was blocked forever. This is what happened in the recent production incident: roughly 40 users were rate-limited indefinitely and had to be cleared by hand from Redis.

`check` now issues both commands in a single pipeline, so INCR and EXPIRE are sent together and there is no window in which one lands without the other. The EXPIRE uses `nx=True` rather than the previous `count == 1` guard, which pushes the "only set a TTL if there isn't one" decision into Redis instead of inferring it from the counter value. That also repairs the case the old guard missed: a key that somehow already exists without a TTL now gets one on the next check, rather than staying unbounded until someone intervenes.

Behaviour is otherwise unchanged. The window is still measured from the first request in a period, and the limit comparison is the same, so callers see no difference in when they are throttled.

The new test in `tests/test_ratelimit.py` covers the crash scenario directly, asserting that a key created through `check` always carries a TTL even when the sequence is interrupted after the increment. Note that `nx` on EXPIRE requires Redis 7.0 or later; deployments on 6.x will raise on the pipeline execution, so the server version should be confirmed before this ships.