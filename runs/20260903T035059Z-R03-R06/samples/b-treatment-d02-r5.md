**Fix rate-limit keys that could be left without a TTL**

`RateLimiter.check` issued `INCR` and `EXPIRE` as two separate round trips to Redis, so any crash or timeout in the gap between them left the counter key with no expiry. Once that happened, the key stayed above the limit forever and the affected caller was locked out until someone deleted it by hand. This is what caused last week's incident, in which roughly 40 users were rate-limited indefinitely and had to be cleared manually from Redis.

Both commands now go out in a single pipeline, so they are sent together and the key can no longer survive with a missing TTL. The `EXPIRE` also uses `nx=True` rather than being guarded by a `count == 1` check on the client side: the previous form only set a TTL on the very first increment, which meant a key that somehow lost its expiry could never regain one, whereas `nx` lets Redis itself decide and sets the TTL whenever none is present. Behaviour for the normal path is unchanged, since the window is still measured from the first request in a window and is not extended by subsequent ones.

The new test in `tests/test_ratelimit.py` covers the failure directly by simulating a process death between the increment and the expiry, asserting that the key still carries a TTL afterwards. It fails against the old two-round-trip implementation.

Reviewers should confirm that the deployed Redis is 7.0 or later, since `EXPIRE` gained the `NX` flag in 7.0 and will raise an error on older servers.