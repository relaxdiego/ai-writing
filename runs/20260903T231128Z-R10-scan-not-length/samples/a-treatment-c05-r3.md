I did not find the cause. What I have is a strong timing correlation and an unverified mechanism behind it.

August has 147 "session expired" lines, and the four largest clusters all fall in the 09:00 hour of a Friday:

| Hour | Count |
|---|---|
| 2026-08-14T09 | 19 |
| 2026-08-21T09 | 16 |
| 2026-08-07T09 | 14 |
| 2026-08-14T13 | 9 |
| 2026-08-28T09 | 7 |

`deploy/cron.d/rotate-session-keys` runs `0 9 * * 5`, which is 09:00 every Friday. That is the same wall clock, on the same weekday, as the top three buckets.

The correlation does not close the case, for two reasons. Those four Friday-09:00 buckets total 56 of 147 events, so more than half the sign-outs happen at some other time, and I only looked at the top five hours, so I have no idea how the remaining 82 are distributed. And `rotate_key` in `src/auth/keys.py:31` is written specifically to prevent this: it moves the current key to `previous` before installing the new one, and the comment says existing sessions keep working. I never traced the verification path, so I cannot tell you whether anything actually reads `previous` when the current key fails.

That is where I would look next, in this order:

1. Find the token verification code and confirm it falls back to `store.get("previous")`. If it does not, the comment is aspirational and every rotation invalidates every live session, which would produce a much larger spike than 19 people, so something else would still need explaining.
2. Check the write order at `keys.py:33-35`. `current` is set before `previous`. In the window between those two writes, `current` is the new key while `previous` still holds the key from the *prior* rotation, one generation too old. A request landing in that window would fail both lookups. The window is milliseconds, which fits the small victim count, but I have not confirmed the store lacks a transaction around it or that verification is even reachable in that window.
3. Explain the non-Friday events, including the 9 at 2026-08-14T13. If key rotation is the whole story, those should not exist.

Two things about the numbers themselves. The device breakdown (61 android, 44 iphone, 31 chrome-desktop, 11 safari-desktop) tells you nothing without baseline traffic per platform; mobile may simply be most of your traffic. And the hour counts came from `uniq -c` without a preceding `sort`, so they are only correct if the log is written in strict timestamp order. If it interleaves across workers, real counts for those hours are higher than shown.

`SESSION_LIFETIME` is 14 days with `remember_me = True`, so ordinary expiry is not a plausible explanation for users being signed out mid-session.