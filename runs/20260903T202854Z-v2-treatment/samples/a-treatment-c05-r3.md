I did not find the cause. What I found is a strong time correlation and an unverified mechanism behind it.

Of the 147 sign-out events in August, 56 fall in the 09:00 hour on 7, 14, 21 and 28 August, all four of which are Fridays. `deploy/cron.d/rotate-session-keys` runs at `0 9 * * 5`, so the largest clusters land exactly on the weekly key rotation. That is the only pattern in the data that lines up with anything in the codebase.

The problem is that the rotation code, as written, should not sign anyone out. `rotate_key()` in `src/auth/keys.py:31` preserves the old key under `previous` specifically so live sessions keep validating, and the 14-day `SESSION_LIFETIME` in `src/auth/config.py:8` is far too long to explain a weekly cadence. So I have a suspect with no demonstrated mechanism, which is not the same as an answer.

Three things I did not check, and any of them could break the correlation or explain it:

- The verification path. I read the writer but never found the reader. If session validation only consults `current` and ignores `previous`, or falls back to it in a way that fails for some token shapes, that closes the gap. If it does read both correctly, the cron is a coincidence and I have nothing.
- The other 91 events. Two thirds of the sign-outs are outside the Friday clusters, including 9 at 13:00 on 14 August. They may be ordinary 14-day expiry, or a second unrelated fault sharing one log message.
- The device skew. Android and iPhone account for 105 of 147, which no part of the rotation story predicts. That skew may just track your traffic mix, but I have not confirmed it against overall session counts, so it might be the real signal and the Friday timing the distraction.

One caveat on my own numbers: the hourly counts came from `uniq -c` without a preceding sort, so they are accurate only if the log is strictly chronological.