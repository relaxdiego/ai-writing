I did not find the cause. What I have is one strong correlation and an unverified suspicion about it.

The sign-out timestamps cluster hard on Friday mornings. Of 147 "session expired" events in August, the top hour-buckets are:

| Bucket | Count | Weekday |
|---|---|---|
| 2026-08-14T09 | 19 | Friday |
| 2026-08-21T09 | 16 | Friday |
| 2026-08-07T09 | 14 | Friday |
| 2026-08-14T13 | 9 | Friday afternoon |
| 2026-08-28T09 | 7 | Friday |

Every Friday in August at 09:00, plus one afternoon spike. The session-key rotation cron in `deploy/cron.d/rotate-session-keys` is `0 9 * * 5` — Friday at 09:00. That is the lead worth chasing.

The reason I am not calling it the cause is that `rotate_key()` in `src/auth/keys.py:31` is written specifically to prevent this. It saves the outgoing key to `store.set("previous", previous)`, and the comment says old sessions keep working. I read the rotation side only. I never checked whether anything on the validation side actually reads `previous` when the current key fails, so I cannot say whether the fallback works, silently does nothing, or was removed at some point. That grep is the single check that would turn this from correlation into a finding, and it is where I would start.

Two things argue against the rotation explaining everything even if the fallback is broken. Those Friday 09:00 buckets account for roughly 56 of 147 events, so more than half the sign-outs happen at other times, including the Friday 13:00 spike that does not line up with the cron at all. And the timestamps I bucketed are whatever timezone the log writes in, which I did not confirm matches the server-local time cron fires in; if they differ, the alignment I am reporting is coincidental and the real cluster sits somewhere else.

The device split — 61 android, 44 iphone, 31 chrome-desktop, 11 safari-desktop — looks like mobile is over-represented at 71% of events, but I never pulled overall traffic by device, so that number may just be what your traffic looks like. I would not read anything into it yet.

`SESSION_LIFETIME` is 14 days with `remember_me = True`, which is consistent with the user reports: nobody is hitting a normal expiry mid-session, so something is invalidating sessions early rather than a lifetime being too short.