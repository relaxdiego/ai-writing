I did not find the cause. What I have is one strong correlation and a lot of unexplained remainder.

The Friday 09:00 clustering is the real signal. August's log holds 147 `session expired` events, and the four largest hour buckets are all 09:00 on a Friday:

| Hour bucket | Events |
|---|---|
| 2026-08-14T09 | 19 |
| 2026-08-21T09 | 16 |
| 2026-08-07T09 | 14 |
| 2026-08-28T09 | 7 |
| 2026-08-14T13 | 9 |

`deploy/cron.d/rotate-session-keys` runs `0 9 * * 5`, which is Friday at 09:00, and every Friday in August landed in that table. That is 56 of the 147 events sitting on top of the key rotation.

The problem is that the code I read says this should not happen. `rotate_key()` in `src/auth/keys.py:31` moves the current key to `previous` before installing the new one, with a comment saying old sessions keep working. So the rotation is doing the thing that would prevent sign-outs, and I have a timing match without a mechanism. The obvious next place to look is the verification path: I only read the rotation function and never checked whether session validation actually falls back to `previous` when the current key fails, or whether `previous` is read at all. A rotation that saves the old key into a slot nobody reads would produce exactly this pattern, but I have not confirmed that either way.

Two other things stay unaccounted for. The remaining 91 events are spread outside the Friday spikes, which is the majority of the total, and nothing in what I looked at explains those. The 9 events at 13:00 on 14 August are a second cluster on a rotation day but four hours later, and I have no story for the gap.

The device breakdown rules out a platform-specific bug: android 61, iphone 44, chrome-desktop 31, safari-desktop 11 covers everything, and no single client is carrying the failures. I could not tell whether those numbers are disproportionate to your traffic mix, since I did not pull session counts per device to compare against.

One caveat on the hour counts: I piped `uniq -c` without sorting first, so those figures are correct only if the log is written in chronological order. If entries interleave, a single hour could be split across several rows and the real spike is larger than what I reported, not smaller.