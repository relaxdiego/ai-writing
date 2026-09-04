I did not find the cause. What I have is one strong-looking correlation that doesn't survive contact with the code, and a majority of the events with no pattern at all.

The timing is the part worth your attention. Of 147 "session expired" events in August, the largest clusters all land in the 09:00 hour on Fridays:

| Bucket | Events |
|---|---|
| 2026-08-14T09 | 19 |
| 2026-08-21T09 | 16 |
| 2026-08-07T09 | 14 |
| 2026-08-28T09 | 7 |
| 2026-08-14T13 | 9 |

`deploy/cron.d/rotate-session-keys` runs `0 9 * * 5`, which is exactly those four Friday mornings. That is a clean match on schedule, and it is why I kept digging there. But `rotate_key` in `src/auth/keys.py:31` explicitly preserves the outgoing key as `previous`, with a comment saying that is precisely so live sessions survive, so the obvious story — rotation invalidates everything signed with the old key — is not what the code says it does. I did not trace the verification path to confirm that `previous` is actually consulted when a token fails against `current`; if it is silently unused, or only consulted on some routes, that would turn the correlation into a cause. That check is the single thing I'd want done before anyone spends effort elsewhere.

There is a narrower hypothesis in the same function that I want to flag without overselling it. The rotation writes `current` before it writes `previous`, so for the interval between those two `store.set` calls, `previous` still holds the key from the rotation before last and the just-retired key is momentarily accepted nowhere. A request landing in that window would fail. The window is presumably sub-second, which makes it a poor explanation for nineteen sign-outs in one hour, so I mention it as a thing to fix on its own merits rather than as an answer.

The correlation also doesn't cover the problem. Those four Friday buckets are roughly 56 of 147 events. The rest, including the nine at 13:00 on the 14th, are scattered with no shape I could find, so even a confirmed rotation bug would leave more than half of the reports unexplained. The device breakdown (61 android, 44 iphone, 31 chrome-desktop, 11 safari-desktop) told me nothing either, because I never pulled session counts per platform to compare against, and without denominators that split is as likely to be your traffic mix as a signal.

One thing that is ruled out: `SESSION_LIFETIME` is 14 days with `remember_me` enabled, so ordinary lifetime expiry is not what these people are hitting mid-session.