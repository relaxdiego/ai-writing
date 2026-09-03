I did not find the cause. What I found is a timing correlation strong enough to be worth naming, and a gap in it I could not close.

The sign-out events cluster on Fridays at 09:00. The top buckets in the August log are 2026-08-07T09, 2026-08-14T09, 2026-08-21T09 and 2026-08-28T09, which are the four Fridays in the month, and the key-rotation cron in `deploy/cron.d/rotate-session-keys` runs `0 9 * * 5`. That is the same hour on the same weekday, four times out of four.

The problem is that the rotation code looks like it should tolerate this. `rotate_key()` in `src/auth/keys.py:31` moves the current key into `previous` before installing the new one, with a comment saying existing sessions are meant to keep working. So either the verification path never falls back to `previous`, or something else is happening at 09:00 on Fridays. I did not read the verification path, so I cannot tell you which.

Three things are still open:

- Whether session-token verification actually tries the `previous` key, or only `current`. This is the single check most likely to settle it, and I have not done it.
- The 09:00 Friday buckets account for 56 of 147 events. The rest are spread across the month, including a cluster of 9 at 2026-08-14T13 that the cron does not explain. A rotation bug would not produce those.
- The cron file is dated Jan 12 2026 and I only searched the August log. If July shows the same Friday spike, this is chronic rather than a recent regression, and it stops matching "users started reporting this."

One thing I would not read much into yet: the device split of 61 android, 44 iphone, 31 chrome-desktop, 11 safari-desktop is raw counts, not rates. Without the traffic mix underneath it, that distribution may be nothing more than which devices your users are on.

`SESSION_LIFETIME` is 14 days with `remember_me = True` (`src/auth/config.py:8`), so ordinary expiry is not a plausible explanation for someone being signed out mid-session, and it does not explain a weekly rhythm either.