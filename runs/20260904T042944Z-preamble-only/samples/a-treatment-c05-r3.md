I did not find the cause. What I have is a timing correlation strong enough to chase and thin enough that I would not act on it yet.

There were 147 sign-out events in the August log. The device split is 61 android, 44 iphone, 31 chrome-desktop, 11 safari-desktop, which is roughly an ordinary traffic mix and gives no sign of a client-specific bug. Plain expiry is also a poor fit: `SESSION_LIFETIME` is 14 days with `remember_me` on, so anyone active in the last fortnight should not be timing out mid-visit.

The timestamps are where it gets interesting. The largest buckets:

| Hour bucket | Events | Day |
|---|---|---|
| 2026-08-14T09 | 19 | Friday |
| 2026-08-21T09 | 16 | Friday |
| 2026-08-07T09 | 14 | Friday |
| 2026-08-14T13 | 9 | Friday |
| 2026-08-28T09 | 7 | Friday |

Four of the five are Friday at 09:00, and `deploy/cron.d/rotate-session-keys` runs `0 9 * * 5` — Friday at 09:00. That is a clean match on the hour.

What stops me calling it the cause is that the rotation code looks like it was written specifically to avoid this. `rotate_key()` moves the current key to `previous` before installing the new one, and the comment says existing sessions keep working. I only read the write side. I have not opened the code that validates an incoming session token, so I do not know whether it ever falls back to `store.get("previous")` on a signature mismatch. Until someone reads that path, the rotation theory is a coincidence of scheduling, not a mechanism.

There is also an accounting gap that the theory does not close. The four Friday 09:00 buckets total 56 events out of 147. Even if key rotation explains every one of them, about ninety sign-outs happened at other times, including nine on 14 August at 13:00. Either there is a second cause, or ordinary expiries share the same log message and I cannot separate them from the text alone. One caveat on my own numbers: the hourly histogram piped `awk` into `uniq` without sorting first, so it only collapses adjacent lines. If the log is strictly chronological the counts hold, but if writers interleave, the buckets are fragmented and the real Friday totals are higher than what I reported.

The next thing to read is the session validation path in `src/auth/`, specifically whether a failed signature check retries against the previous key or gives up.