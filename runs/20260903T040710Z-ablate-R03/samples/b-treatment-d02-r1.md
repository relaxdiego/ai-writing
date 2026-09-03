**Fix permanent lockout when rate-limit keys are created without a TTL**

`RateLimiter.check` incremented the counter and set its expiry as two separate Redis round trips, so any crash, timeout, or dropped connection between the two left a key that counted requests forever and never expired. Once a key crossed the limit in that state, the caller was rate-limited indefinitely with no way to recover on its own. This happened in production: roughly 40 users were locked out until we deleted their keys from Redis by hand.

The two commands now go out in a single pipeline, so they are sent together and the window is always applied to a key we just incremented. The `EXPIRE` uses `nx=True` rather than the previous `count == 1` guard, which keeps the semantics the same (only the first request in a window sets the TTL) while moving the decision to Redis instead of relying on a return value the client has to interpret. That also closes a smaller variant of the same bug, where two concurrent callers could both observe a count other than 1 for a key whose TTL had not been set yet.

The accompanying test simulates a failure between the increment and the expiry and asserts the key still carries a TTL afterwards, which fails against the old implementation.

Existing keys stuck without a TTL are not repaired by this change; they will need the same manual clearing as during the incident, or a one-off sweep for rate-limit keys where `TTL` returns `-1`.