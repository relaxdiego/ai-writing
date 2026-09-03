## Make rate-limit key expiry atomic

`RateLimiter.check` issued `INCR` and `EXPIRE` as two separate round trips to Redis, so the TTL was only set on the counter after a second command succeeded. If the process crashed or the connection timed out in the gap between them, the key survived with no expiry, and since the counter never reset, the caller was rate-limited for good. We hit exactly that in production: roughly 40 users were locked out indefinitely and their keys had to be deleted from Redis by hand.

This change collapses both commands into a single pipeline so they are sent and executed together, closing the window in which a key can exist without a TTL. The `EXPIRE` also moves to `nx=True`, which restores the behaviour the old `if count == 1` guard was there to provide — the TTL is set when the key is first created and is not pushed forward by later increments, so a client making steady requests still has its window end at a fixed time rather than sliding indefinitely.

Behaviour is otherwise unchanged: the same counter is incremented, the same limit comparison decides the return value, and callers see no difference in the normal path.

### Testing

Added `test_expiry_survives_crash_between_incr_and_expire`, which covers the failure mode directly by asserting the key carries a TTL after the interrupted sequence.

### Notes for review

Pipelining here is not transactional in the `MULTI`/`EXEC` sense unless the client is configured for it, but it does mean both commands leave the client in one write and are executed back to back by the server, which removes the application-side crash window that caused the incident. Keys already stranded without a TTL in production were cleared manually and are not addressed by this change; if any remain, they will need the same treatment.