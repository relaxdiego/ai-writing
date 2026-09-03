**Make the rate-limit window atomic with the counter**

`RateLimiter.check` incremented the key and set its TTL as two separate round trips, setting the expiry only when the counter came back as 1. If the process died or the connection timed out in the gap between them, the key survived with no TTL and never decayed. Every subsequent request for that key incremented a counter that could only go up, so the caller was locked out for good.

That happened in production: roughly 40 users were rate-limited indefinitely and had to be cleared out of Redis by hand.

Both commands now go through a single pipeline, so `INCR` and `EXPIRE` reach Redis as one transaction and either both apply or neither does. The `EXPIRE` carries `nx=True` rather than being guarded by a `count == 1` check on the client side, which keeps the semantics the same (the window is set once, at the start, and is not extended by later requests) while moving the condition to where the data is. It also means any key that already lost its TTL gets one back on its next request, so the surviving damage from this class of failure heals itself instead of needing manual cleanup.

The new test covers the crash window directly: it asserts the key carries a TTL after a failure injected between the increment and the expiry.

One deployment note: `EXPIRE ... NX` requires Redis 7.0 or later. Our production and staging clusters are on 7.2, but anyone running an older Redis locally will see the `expire` call rejected.