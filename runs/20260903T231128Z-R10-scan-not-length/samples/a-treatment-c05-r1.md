I did not find the cause. What I have is a timing correlation that fits well enough to be worth chasing but that I could not close, plus a specific piece of code I never read.

The 147 "session expired" events in August are not spread evenly. The largest clusters:

| Hour | Events | Day |
|---|---|---|
| 2026-08-07 09:00 | 14 | Friday |
| 2026-08-14 09:00 | 19 | Friday |
| 2026-08-21 09:00 | 16 | Friday |
| 2026-08-28 09:00 | 7 | Friday |

Those are the four Fridays in August 2026, and `deploy/cron.d/rotate-session-keys` runs `0 9 * * 5`, which is Friday at 09:00. Fifty-six of the 147 events fall inside those four hours. (The hour histogram used `uniq -c` without a preceding sort, so it only collapses adjacent lines; if the log is not strictly chronological the real clusters are larger than shown, not smaller.)

The rotation code itself reads as correct on its face. `rotate_key()` copies the current key into `previous` before writing the new one, and the comment says existing sessions keep working. But I only read the writer. I never opened the code that validates an incoming session token, so I cannot tell you whether `previous` is actually consulted during verification. If it is not, every session signed with the outgoing key dies at 09:00 on Friday, which is exactly the shape in the log. There is also a smaller window in `rotate_key` itself: `store.set("current", new)` and `store.set("previous", previous)` are two separate writes, so a request landing between them sees the new current key alongside a `previous` that is still a generation stale. That would produce a handful of failures at precisely that minute rather than a sustained outage. Reading the verification path in `src/auth/` is what settles which, if either, of these is real.

Ninety-one events remain unexplained by any of this. They are scattered, and one visible cluster (nine events at 2026-08-14 13:00) is nowhere near a rotation. So even if the key handling turns out to be broken, it is not the whole story.

Two things I could not interpret. The platform skew is heavy toward mobile, 61 android and 44 iphone against 42 desktop, but I never pulled overall traffic by platform, so I do not know whether that is a signal or just the traffic mix. And the field positions in those `awk` calls (`$4` for platform, `$1` for timestamp) were inferred from the log's shape rather than from a format definition; if the log lines vary, the breakdown is unreliable.

One thing this does rule out. `SESSION_LIFETIME` is 14 days with `remember_me` enabled, so ordinary expiry should not be signing out people who are actively using the site, which matches your report that it happens mid-session.