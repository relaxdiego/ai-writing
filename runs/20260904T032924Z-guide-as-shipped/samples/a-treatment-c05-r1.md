I did not find the cause. What I have is a strong correlation and no mechanism to back it up, so treat the below as a lead rather than an answer.

The sign-outs cluster on Friday mornings. Every date in the top of the hourly histogram is a Friday in August 2026, all in the 09:00 hour, and the session-key rotation cron is scheduled for exactly that slot:

| Hour bucket | Sign-outs | Day |
|---|---|---|
| 2026-08-14T09 | 19 | Friday |
| 2026-08-21T09 | 16 | Friday |
| 2026-08-07T09 | 14 | Friday |
| 2026-08-28T09 | 7 | Friday |
| 2026-08-14T13 | 9 | Friday afternoon |

`deploy/cron.d/rotate-session-keys` runs `0 9 * * 5`, and `rotate_key()` in `src/auth/keys.py:31` is the thing that fires. That is where I'd expect the story to end, except the code looks like it was written to prevent this: it reads the current key, installs a new one, and stores the old one under `previous`, with a comment saying old sessions keep working. So the rotation is designed to be non-disruptive, and I have not shown that it isn't.

The gap in what I checked is the verification side. I never read the code that validates an incoming session token, so I don't know whether it actually tries `previous` when `current` fails, or whether `previous` is consulted only in some paths. A rotation that writes a fallback key nobody reads would produce exactly this pattern, but I have not opened that file and I am not going to assert it.

Two things also don't fit the theory. The Friday 09:00 buckets account for 56 of the 147 events, so more than half the sign-outs happen at times the cron doesn't explain, including the 13:00 cluster on 14 August. And the platform skew is unaccounted for: android and iphone together are 105 of 147 against 42 for desktop, which a server-side key rotation should not care about at all. That split points at something in mobile session handling — app backgrounding, token refresh on resume — that is a separate line of enquiry from the cron.

One caveat on the correlation itself: I compared cron times against log timestamps without confirming both are in the same timezone. If the log is UTC and cron runs in the host's local zone, the alignment I'm relying on may be coincidental.