I did not find the cause. Here's what I have.

## The one real signal: the sign-outs cluster on the key-rotation schedule

The `session expired` timestamps bunch into the 09:00 hour of 2026-08-07, 08-14, 08-21, and 08-28 — every Friday in August. The rotation cron is:

```
0 9 * * 5 /usr/local/bin/rotate-session-keys
```

`0 9 * * 5` is 09:00 Friday. That's an exact match, and it's the sort of thing users would experience as "signed out in the middle of using the site" rather than as an expiry.

Two caveats on how strong this is:

- **It covers about 40% of the events, not all of them.** The Friday-09:00 buckets total roughly 56 of 147. The rest are scattered, including a 9-event bucket at 2026-08-14T13. So there is a baseline of ordinary expiries mixed in, and I can't yet tell which reports from your users belong to which population.
- **The code says this shouldn't happen.** `rotate_key()` in `src/auth/keys.py:31` deliberately preserves the old key so existing sessions survive. So the correlation points at rotation, but the intended design contradicts it. I have a *when*, not a *why*.

## Why I stopped short

I never read the verification path. I found where keys are written but not where they're read, so I can't tell you whether the preserved `previous` key is actually consulted when a token fails against `current`. That's the gap between a correlation and a cause, and it's the next thing to look at.

Worth noting the shape of the failure constrains the explanation: if the `previous` fallback were simply dead code, *every* active session would break at 09:00 Friday, and you'd see far more than 19 events. So it's more likely something narrow. One hypothesis I'd test first — `rotate_key()` writes `current` and then `previous` as two separate non-atomic `store.set` calls. In the window between them, `previous` still holds the key from *last* week while `current` holds the new one, so a request arriving in that gap has neither key that signed its token. That would hit a small, effectively random set of users, which matches "a small number of people" and matches your inability to reproduce it.

That is a hypothesis, not a finding. I haven't confirmed the store isn't transactional, and I haven't confirmed the read path behaves as I'm assuming.

## What I'd check next

1. The verify/decode function — does it retry against `previous` on failure, and does it read both keys as a single consistent snapshot?
2. Whether app servers cache these keys in-process. A cached copy on one instance would produce exactly this scattered, hard-to-reproduce pattern, and would also explain events outside the 09:00 window.
3. Whether the non-Friday events have a different log signature from the Friday ones — that tells you whether you're chasing one bug or two.

## Two things I looked at that led nowhere

`SESSION_LIFETIME = timedelta(days=14)` and `remember_me = True` (`src/auth/config.py:8-9`) are both unremarkable and don't explain mid-session sign-outs.

The client breakdown skews mobile — android and iphone are 105 of 147 — but I have no traffic denominator, so I can't say whether that's a real signal or just your traffic mix. Don't read anything into it without a baseline.