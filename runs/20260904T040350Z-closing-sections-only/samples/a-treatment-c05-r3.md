I did not find the cause. What I have is a strong timing correlation with no mechanism behind it.

The 147 sign-outs in August are not spread evenly. Every one of the four largest hourly buckets falls at 09:00 on a Friday:

| Date | Sign-outs at 09:00 |
|---|---|
| 2026-08-07 | 14 |
| 2026-08-14 | 19 |
| 2026-08-21 | 16 |
| 2026-08-28 | 7 |

The session key rotation cron is `0 9 * * 5`, which is Friday at 09:00. Two caveats on those numbers before you lean on them: I compared the cron schedule against log timestamps without confirming both are in the same timezone, and my hourly count relied on the log being in chronological order. If the cron host runs local time while the log is UTC, the alignment is coincidence.

The reason I couldn't close it is that the code looks correct. `rotate_key` in `src/auth/keys.py:31` moves the outgoing key into the `previous` slot, so a session signed with it should still verify after a rotation. Nothing I read explains how rotation alone would sign anyone out.

One hypothesis is worth naming, though I did not test it. Only two keys are ever held, so any given key is usable for at most two rotation intervals, or 14 days. A session created shortly before a rotation is signed with a key that has already spent most of its first interval, so it loses its key after roughly seven days even though `SESSION_LIFETIME` promises fourteen. That would affect only people who signed in during the hours before a Friday rotation and came back about a week later, which is consistent both with the small numbers and with your inability to reproduce it. Confirming or killing it means reading how verification actually walks the `current` and `previous` slots, which I did not do. The log lines would settle it faster: they record that a session expired but not which key verified it, or whether that key was current or previous.

Against all of that, 91 of the 147 events sit outside those four Friday buckets, including nine at 13:00 on 2026-08-14. Either there is a second cause or the rotation story is wrong. I also can't read anything into the device split (61 android, 44 iphone, 31 chrome-desktop, 11 safari-desktop) because I never pulled the baseline traffic mix to compare it against.