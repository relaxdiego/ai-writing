**Fix rate limiter losing TTL when INCR and EXPIRE are split across round trips**

## Problem

`RateLimiter.check` issued `INCR` and `EXPIRE` as two separate Redis calls, setting the TTL only when the counter came back as `1`. If the process crashed or the connection timed out between those calls, the key was left with no expiry. Since the counter never reset and the `count == 1` branch never fired again, the key stayed above the limit forever and the caller was locked out permanently.

This happened in production: roughly 40 users were rate-limited indefinitely and had to be cleared out of Redis by hand.

## Change

Both commands now go out in a single pipeline, and `EXPIRE` uses `nx=True` so it only sets a TTL when none exists. The pipeline removes the window where a crash can land between the two commands, and `nx` keeps the repeated `EXPIRE` from extending the window on every request, which is what the old `count == 1` check was there to prevent.

## Tests

Adds a test covering the crash-between-INCR-and-EXPIRE case: the key must end up with a TTL regardless of where the failure occurs.

## Notes for reviewers

`EXPIRE ... NX` requires Redis 7.0+.