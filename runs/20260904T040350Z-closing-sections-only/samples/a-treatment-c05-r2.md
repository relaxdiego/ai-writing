I did not find the cause. What I have is a timing correlation strong enough to be worth chasing and a mechanism I could not confirm.

The August log holds 147 `session expired` events, and the heaviest buckets all land at 09:00 on a Friday:

| Bucket | Weekday | Events |
|---|---|---|
| 2026-08-14T09 | Friday | 19 |
| 2026-08-21T09 | Friday | 16 |
| 2026-08-07T09 | Friday | 14 |
| 2026-08-14T13 | Friday | 9 |
| 2026-08-28T09 | Friday | 7 |

`deploy/cron.d/rotate-session-keys` fires at `0 9 * * 5`, which is 09:00 every Friday, so the session key rotates at exactly the hour those spikes occur. That is where I stopped being able to make progress. `rotate_key()` in `src/auth/keys.py:31` does what its comment claims: it reads the current key, generates a new one, and writes the old value to `previous` before returning. Nothing there discards a key that live sessions still depend on. For rotation to sign anyone out, the verification path would have to fail to consult `previous`, or consult it in a way that misses some cookies, and I never read the verification path, so I am asserting a correlation and not a mechanism. Two other things would need checking before even the correlation is solid: whether the log timestamps and the cron schedule are in the same timezone, and whether `previous` survives a process or deploy restart rather than living only in memory.

The correlation also does not cover the whole problem. The four Friday 09:00 buckets account for 56 of the 147 events, so roughly a third. The remaining events are spread thinly enough that none of them reached the top five, and the 13:00 bucket on 14 August has nine events with no rotation anywhere near it. Whatever is happening at 09:00 on Fridays, something else is signing people out the rest of the week.

The device split is 61 android, 44 iphone, 31 chrome-desktop, 11 safari-desktop. I would not read anything into that yet. It sums to the full 147, which means every affected session is in one of those four buckets, but I have no traffic baseline to compare it against, and a 71% mobile share among the failures is unremarkable if 71% of your sessions are mobile. Getting that baseline is the cheapest way to tell whether the platform breakdown is a lead or just a reflection of who uses the site.