I did not find the cause, but the timing lines up with weekly key rotation closely enough that I'd start there.

Of 147 "session expired" events in the August log, the four biggest hourly clusters are 2026-08-07T09, 08-14T09, 08-21T09 and 08-28T09 — every Friday in the month, all at 09:00. `deploy/cron.d/rotate-session-keys` runs `0 9 * * 5`, which is 09:00 every Friday. That is 60 of the 147 events landing in the same hour as the rotation job.

What I could not do is show a mechanism. `rotate_key` in `src/auth/keys.py:31` deliberately keeps the outgoing key as `previous` so live sessions survive, and on its face that should prevent exactly this. The one thing in the code that doesn't add up is the arithmetic between the two settings: rotation is weekly and keeps one generation of history, but `SESSION_LIFETIME` in `src/auth/config.py:8` is 14 days. A session signed 8 to 14 days ago was signed with a key that is now two generations old, so it is neither `current` nor `previous`. That would sign out a thin slice of long-lived sessions at each rotation while leaving everyone from the past week alone, which is the shape the user describes and the reason it doesn't reproduce on demand.

I have not confirmed that, and these are the specific gaps:

- I never read the token verification path, so I don't know that it consults only `current` and `previous`. If it walks a longer key history, the hypothesis is dead.
- The remaining 87 events are unaccounted for, including a 14-event cluster at 08-14T13 that doesn't fall on a rotation.
- I didn't check whether log timestamps and the cron server share a timezone, so the 09:00 alignment could be coincidence.
- The device split (61 android, 44 iphone against 42 desktop) is unexplained. Mobile sessions plausibly live longer between logins, which fits the ageing-key story, but I have no data tying device to session age.

The correlation is strong enough to act on and too thin to call a diagnosis. Reading the verify function and pulling session-creation ages for the accounts in the Friday clusters would settle it either way.