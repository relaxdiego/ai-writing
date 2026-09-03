I did not find the cause. What I did find is a timing correlation strong enough to be worth chasing, plus the code path I would read next.

Across `logs/app-2026-08.log` there are 147 "session expired" events for August. Broken down by client they look like ordinary traffic: 61 android, 44 iphone, 31 chrome-desktop, 11 safari-desktop. No single platform or app version stands out, which argues against a client-side bug and is consistent with your users not being able to reproduce it on demand.

The timestamps are the interesting part. The largest clusters all fall in the 09:00 hour of 2026-08-07, 08-14, 08-21 and 08-28, which are the four Fridays in the month, totalling about 56 of the 147 events. `deploy/cron.d/rotate-session-keys` runs `0 9 * * 5`, so weekly key rotation fires at exactly that hour. Two caveats on those numbers: `uniq -c` was run without sorting first, so it counts contiguous runs rather than true per-hour totals (fine if the log is strictly chronological, misleading if it isn't), and I did not check that the log timestamps and the cron schedule are in the same timezone.

`rotate_key()` in `src/auth/keys.py:31` keeps one previous key, and its comment says that is what lets existing sessions survive. But `SESSION_LIFETIME` is 14 days and rotation is every 7, so a session can outlive two rotations while only one old key is retained. A session signed shortly before a rotation has its key demoted to `previous` almost immediately and evicted a week later, while the session itself is only about seven days old and still valid by policy. That would sign out a user mid-use, and only users who happen to be active at 09:00 on a Friday would notice, which fits the small numbers.

I have not confirmed that mechanism, and it is a hypothesis rather than a finding. Three things would settle it:

- The session validation path, which I have not read. If it never falls back to `previous`, the retention of the old key is decorative and the failure window is much wider than I described.
- Whether sessions are re-signed with the current key on each request. If they are, only users idle for more than a week would be hit, and the counts should be much smaller than 19 in an hour.
- The rotation job's own logs, to confirm it actually ran at those four timestamps rather than the correlation being coincidental.

The roughly 90 events outside the Friday 09:00 windows are unaccounted for. Some are presumably ordinary 14-day expiries, but the run of 9 at 2026-08-14T13 is a second cluster on a rotation day and does not fit that explanation.