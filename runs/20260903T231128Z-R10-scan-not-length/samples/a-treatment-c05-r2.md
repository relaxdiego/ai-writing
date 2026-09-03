I did not find the cause, but the timing correlation is strong enough that I'd start here.

The 147 "session expired" events in August are not spread evenly. The four largest clusters all land at 09:00 on a Friday, which is exactly when `deploy/cron.d/rotate-session-keys` fires (`0 9 * * 5`):

| Timestamp | Events | Weekday |
|---|---|---|
| 2026-08-14T09 | 19 | Friday |
| 2026-08-21T09 | 16 | Friday |
| 2026-08-07T09 | 14 | Friday |
| 2026-08-28T09 | 7 | Friday |
| 2026-08-14T13 | 9 | Friday |

The 13:00 cluster on the 14th does not fit the pattern, and the five rows above account for only 65 of the 147 events, so whatever is happening at rotation time is not the whole story.

The comment in `src/auth/keys.py:29` says old sessions keep working because the previous key is retained, and `rotate_key` does write `previous` before overwriting `current`. What I did not do is read the code that verifies an incoming session token, so I cannot tell you whether the previous key is ever actually consulted on the verification path. If it isn't, every rotation invalidates every session at once and the correlation is fully explained. That check is the first thing to do.

There is a second possibility that survives even if the fallback works correctly. Keeping two keys with weekly rotation gives any individual key a useful life of one week as `current` plus one as `previous`. A session signed shortly before a rotation is therefore backed by a key that disappears about seven days later, not the fourteen that `SESSION_LIFETIME` in `src/auth/config.py:8` promises. Sessions between roughly seven and fourteen days old would be the ones dropped, which fits both the small number of affected people and their inability to reproduce it on demand.

The device split (61 android, 44 iphone, 31 chrome-desktop, 11 safari-desktop) leans mobile, which is consistent with long-lived backgrounded sessions being the ones caught, but I have no baseline traffic mix to compare against, so it may just reflect who uses the site.

One caveat on the correlation itself: the log timestamps are ISO-formatted and I assumed they share a timezone with the cron daemon. If the app logs UTC and the host runs on something else, the 09:00 alignment is coincidental and the whole chain above collapses.