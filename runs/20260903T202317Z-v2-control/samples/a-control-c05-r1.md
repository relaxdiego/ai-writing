I did not find the cause. Here's what I have.

## The one strong signal

The sign-outs cluster hard on Friday mornings at 09:00 UTC:

| Bucket | Count |
|---|---|
| 2026-08-14T09 | 19 |
| 2026-08-21T09 | 16 |
| 2026-08-07T09 | 14 |
| 2026-08-28T09 | 7 |

Aug 7, 14, 21 and 28 are all Fridays. `deploy/cron.d/rotate-session-keys` is `0 9 * * 5` — Friday 09:00. That is the same slot, every week, for four weeks.

That is a timing correlation and nothing more. I did not establish a mechanism, and the code I read argues against the obvious one: `rotate_key()` in `src/auth/keys.py:31` keeps the old key in `previous`, which is exactly what you'd do to stop rotation from invalidating live sessions.

## What I did not check (the gap that matters most)

I grepped for the *writer* of the key store and never looked at the *reader*. I have not seen the verification path, so I don't know whether session validation actually falls back to `previous`, or only ever consults `current`. If it doesn't fall back, the comment on line 29 is describing an intent the code doesn't implement, and everything above snaps into place. That's the first thing to look at.

A second, weaker hypothesis I couldn't test: `SESSION_LIFETIME` is 14 days (`src/auth/config.py:8`) and rotation is weekly, so a 14-day session spans two rotations, while the store only retains two keys. A session signed under a key that is two rotations old would be unverifiable while still nominally valid. Whether that actually bites depends entirely on the same verification code I haven't read.

## What the Friday theory does not explain

The spikes are about 56 of 147 events — roughly 38%. The majority of sign-outs are scattered outside those windows and are unaccounted for. There's also a 9-event cluster at 2026-08-14T13, four hours after that day's rotation, which I can't attribute to anything.

Two caveats on the numbers themselves: the hourly counts came from `uniq -c` without a sort, so they're only correct if the log is written in chronological order — worth confirming before leaning on the percentages. And the device split (105 of 147 mobile) means nothing without your baseline traffic mix; I never pulled one, so I can't say mobile is over-represented.

## Suggested next step

Read the session-verification path and confirm whether it tries `previous` on a `current` miss. If it does, the Friday correlation is probably coincidental to something else running in that cron slot and I'd want the deploy logs for those four timestamps. Want me to go after the verification code?