I did not find the cause. What I have is a timing correlation strong enough to be worth acting on, and a mechanism I could not confirm because I never read the code that validates a session key.

The sign-outs cluster hard on Friday mornings at 09:00, which is exactly when `deploy/cron.d/rotate-session-keys` fires (`0 9 * * 5`). August 7, 14, 21 and 28 were all Fridays:

| Hour | Events |
|---|---|
| 2026-08-14T09 | 19 |
| 2026-08-21T09 | 16 |
| 2026-08-07T09 | 14 |
| 2026-08-14T13 | 9 |
| 2026-08-28T09 | 7 |

That accounts for 56 of the 147 August events, so roughly 40% of the reports line up with key rotation and the other 60% are scattered across the month with no pattern I could see. The 09:00 spike is too clean to be coincidence, but it is also not the whole story.

The hypothesis I could not verify: `rotate_key()` in `src/auth/keys.py:31` keeps exactly one generation of old key, moving `current` into `previous` and discarding whatever was in `previous` before. Rotation is weekly, but `SESSION_LIFETIME` in `src/auth/config.py:8` is 14 days with `remember_me = True`. A session signed 8 to 14 days ago was signed with a key that is now two generations old, so its key is gone from the store while the session itself is still inside its lifetime. Those users would be signed out mid-use, on a Friday at 09:00, and would be a minority of the user base at any given rotation, which matches the report. The comment on line 29 says old sessions keep working, and for a one-week-old session it is right; it is the second week the comment does not cover.

What would settle it, and what I did not do:

- Read the session verification path to confirm it falls back to `previous` and does nothing else, such as consulting a third key or a separate cache.
- Check whether the app runs on multiple instances that each execute the cron, since two rotations in quick succession would evict a still-valid key even for one-week-old sessions.
- Pull the actual session ages for the users in the Friday 09:00 buckets, which is the direct test of the two-generation gap and needs data I did not find in the log.
- Account for the off-peak events, including the 9 at 13:00 on August 14, which no rotation explains.

On devices, the breakdown is 61 android, 44 iphone, 31 chrome-desktop, 11 safari-desktop. Mobile is 105 of 147, but I have no traffic baseline to compare against, so I cannot tell whether mobile is genuinely over-represented or just more numerous.