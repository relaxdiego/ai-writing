I did not find the cause. What I have is a strong lead and the reason I could not close it.

The sign-outs cluster on Friday mornings at 09:00, which is exactly when the session key rotation cron fires (`deploy/cron.d/rotate-session-keys` is `0 9 * * 5`, and 2026-08-07, 08-14, 08-21 and 08-28 are all Fridays):

| Hour bucket | Events |
|---|---|
| 2026-08-14T09 | 19 |
| 2026-08-21T09 | 16 |
| 2026-08-07T09 | 14 |
| 2026-08-28T09 | 7 |
| 2026-08-14T13 | 9 |

That correlation is what makes rotation the obvious suspect, but it does not survive as an explanation on its own. `rotate_key()` in `src/auth/keys.py:31` deliberately preserves the outgoing key as `previous`, with a comment saying existing sessions keep working, so on its face rotation should be invisible to users. I did not read the verification path to check whether `previous` is actually consulted when a session cookie fails against `current`, and until someone does, the correlation is unexplained rather than understood.

Two other things are worth putting in front of whoever picks this up. `SESSION_LIFETIME` is 14 days (`src/auth/config.py:8`) while rotation is weekly and only one previous key is retained, so a session that survives two rotations has its signing key dropped from the store while the session is still nominally valid. That is arithmetic, not evidence, and I have not confirmed it produces the log lines we are seeing. Separately, the Friday 09:00 buckets account for 56 of the 147 events in August, so even if rotation explains those, most of the sign-outs happen at other times and need a different explanation. The device skew (105 of 147 on android or iphone) fits a story about long-idle sessions on mobile, but I have nothing beyond the count to support it.

I could not reproduce a sign-out either, and everything above comes from log correlation and reading configuration, not from observing the failure.