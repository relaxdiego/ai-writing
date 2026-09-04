I did not find the cause, but I found a timing correlation strong enough to be worth chasing next.

The 147 sign-out events in August are not spread evenly. Four of the five busiest hours are 09:00 on a Friday, and `deploy/cron.d/rotate-session-keys` runs `0 9 * * 5` — Friday at 09:00.

| Hour | Events | Day |
|---|---|---|
| 2026-08-07T09 | 14 | Friday |
| 2026-08-14T09 | 19 | Friday |
| 2026-08-21T09 | 16 | Friday |
| 2026-08-28T09 | 7 | Friday |
| 2026-08-14T13 | 9 | Friday afternoon |

That accounts for 56 events at the rotation hour, and 65 including the unexplained Friday-afternoon spike, leaving 82 of the 147 scattered elsewhere in the month. So even if rotation turns out to be the mechanism, it explains at most about a third of the reports, and something else is producing the rest.

The reason I am calling this unconfirmed rather than solved is that the comment in `src/auth/keys.py:29` claims the old key is kept so existing sessions keep working, and `rotate_key()` does write the outgoing key to `store.set("previous", previous)`. I never read the verification path, so I do not know whether anything ever reads `previous` back, whether it is consulted before or after the current key, or whether a session signed under the previous key gets silently downgraded rather than accepted. The correlation is consistent both with a bug there and with rotation being a coincidence of Friday-morning traffic. Reading the code that validates an incoming session token against the key store is the one check that would settle it, and it is where I would go next.

Two things I looked at that did not resolve anything. `SESSION_LIFETIME` is 14 days with `remember_me = True`, which is long enough that ordinary expiry should not be producing mid-session sign-outs at this rate. The device breakdown is 61 android, 44 iphone, 31 chrome-desktop, 11 safari-desktop, so mobile is 105 of 147; without a traffic baseline for the same period I cannot tell whether mobile is over-represented or whether that is simply what your traffic looks like, and the difference matters because a mobile skew would point at backgrounded-app token refresh rather than at rotation.

One caveat on the numbers themselves. The hourly counts came from `uniq -c` on unsorted input, which counts consecutive runs rather than totals. For a chronologically ordered log that is the same thing, but if `app-2026-08.log` interleaves writers, every figure in the table is a lower bound and the true Friday concentration could be higher.