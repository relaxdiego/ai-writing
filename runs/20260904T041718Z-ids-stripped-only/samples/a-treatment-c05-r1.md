I did not find the cause. What I have is a strong timing correlation and a piece of code that appears to contradict it.

The 147 sign-out events in August are not spread evenly. The largest clusters all land in the 09:00 hour, and every one of those dates is a Friday:

| Hour | Events |
|---|---|
| 2026-08-14T09 | 19 |
| 2026-08-21T09 | 16 |
| 2026-08-07T09 | 14 |
| 2026-08-28T09 | 7 |
| 2026-08-14T13 | 9 |

`deploy/cron.d/rotate-session-keys` runs `0 9 * * 5`, which is 09:00 every Friday, so the spikes sit exactly on the key rotation. That is where a cause should be, except that `rotate_key()` in `src/auth/keys.py:31` deliberately preserves the old key into `store.set("previous", previous)` so that sessions signed with it keep validating. If that preservation works as the comment claims, rotation should be invisible to users, and I cannot yet explain why it isn't. The gap in my investigation is that I only read the writer: I never traced the validation path to confirm anything actually reads `previous` and retries against it, and I never checked whether a second rotation inside one session lifetime (`SESSION_LIFETIME` is 14 days, so a session spans two rotations) pushes the signing key out of both slots. Either of those would turn "old key is kept" into a comment that is true of the storage and false of the behaviour, but I have not established that either is happening.

Two things also argue against rotation being the whole story. The Friday 09:00 clusters account for 56 events and the odd 13:00 spike on the 14th for 9 more, leaving roughly 82 sign-outs scattered across the month with no visible pattern; whatever explains the spikes leaves most of the volume unexplained. The device breakdown (61 android, 44 iphone, 31 chrome-desktop, 11 safari-desktop) leans mobile, but I pulled no baseline traffic by device, so I cannot say whether that is a signal or just the shape of your user base.

The reproduction difficulty is consistent with all of this: if the trigger is a weekly cron, testing on any other day or hour would show nothing wrong.