I did not find the cause. What I have is a strong timing coincidence with one unverified mechanism behind it, and a residual that the coincidence does not cover.

August has 147 "session expired" lines. Bucketed by hour, the top five are:

| Bucket | Day | Count |
|---|---|---|
| 2026-08-14T09 | Friday | 19 |
| 2026-08-21T09 | Friday | 16 |
| 2026-08-07T09 | Friday | 14 |
| 2026-08-14T13 | Friday | 9 |
| 2026-08-28T09 | Friday | 7 |

Four of those are Friday at 09:00, and `deploy/cron.d/rotate-session-keys` runs `0 9 * * 5`, which is Friday at 09:00. That cron calls `rotate_key()` in `src/auth/keys.py:31`, whose comment says the old key is kept so existing sessions keep working, and the function does write the outgoing key to `store.set("previous", previous)`. What I did not check is the other half of that contract: whether the session verification path actually falls back to `previous` when a token fails against `current`. If it only ever tries `current`, then every session signed before 09:00 on a Friday dies at rotation, the comment is describing an intent the code never completes, and the people affected are whoever happened to be mid-task at that minute. That would also explain why you cannot reproduce it, since you would have to be holding a live session across a Friday morning to see it. Until someone reads the verification code, this is a correlation and not a finding.

The residual matters as much. Those four Friday-09:00 buckets are 56 of 147, so roughly 91 sign-outs happened at other times, including the 9 at Friday 13:00 that the cron does not touch. Either there is a second cause, or the per-hour counts outside the spike are too thin to read as anything but background. Nothing else I looked at narrows it: `SESSION_LIFETIME` is 14 days with `remember_me = True`, which does not produce a mid-session logout, and the device split (61 android, 44 iphone, 31 chrome-desktop, 11 safari-desktop) has no traffic denominator behind it, so I cannot say mobile is over-represented rather than simply more numerous.

One limit on the timing evidence: the cron file has an mtime of 12 January 2026 and I only searched the August log, so I cannot tell you whether the Friday spike is new behaviour or has been there since January. July and earlier logs would settle that, and the key-verification path would settle the mechanism.