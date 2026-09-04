I did not find the cause. What I have is a timing correlation that covers about a third of the events, and one unverified assumption in the key-rotation code.

There were 147 `session expired` events in `logs/app-2026-08.log` for August. The largest clusters land at the same hour on the same weekday:

| Bucket | Count |
|---|---|
| 2026-08-14T09 | 19 |
| 2026-08-21T09 | 16 |
| 2026-08-07T09 | 14 |
| 2026-08-14T13 | 9 |
| 2026-08-28T09 | 7 |

The four 09:00 buckets are the four Fridays of August, and `deploy/cron.d/rotate-session-keys` is `0 9 * * 5`, which is Friday at 09:00. That is why this is hard to reproduce on demand: it needs a session that was already open when the rotation fired.

The rotation itself is supposed to be non-disruptive. `rotate_key()` at `src/auth/keys.py:31` saves the outgoing key into `previous` before writing the new one, and the comment on line 29 says old sessions keep working. I never read the code on the other side of that, the token verification path that is supposed to consume the `previous` slot. If that path only tries `current`, the comment is documenting an intention rather than a behaviour, and every session signed with last week's key dies at 09:00 on Friday. Finding the readers of `previous` is the first thing to settle.

There is a second problem visible in the same function regardless of how verification works. The store holds two generations, `current` and `previous`, so a session survives one rotation and not two. `SESSION_LIFETIME` in `src/auth/config.py:8` is 14 days with `remember_me` on, and 14 days spans two Friday rotations. A session in its second week is unrecoverable even if previous-key verification is working correctly.

Three things keep this short of an explanation. The Friday 09:00 spikes are 56 of 147 events, so the majority sit outside the pattern and need a different cause, including the 9 events at 13:00 on 08-14. The device skew, 105 of 147 from android and iphone, has no traffic baseline behind it, so I cannot tell whether mobile is over-represented or simply the bulk of the traffic. And the timestamp counts came from `uniq -c` on unsorted input, so if the log interleaves at all those numbers are floors rather than totals; re-running that with a `sort` before `uniq` would firm them up.