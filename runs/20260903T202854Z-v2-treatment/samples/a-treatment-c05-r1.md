I have not found the cause. What I have is one strong correlation and a mechanism that, on the code I read, should not produce the symptom.

The sign-outs cluster on Friday mornings at 09:00. Of 147 "session expired" events in August, the four largest hourly buckets are 2026-08-07T09, 08-14T09, 08-21T09 and 08-28T09, all Fridays, totalling 56 events. `deploy/cron.d/rotate-session-keys` fires at `0 9 * * 5`, which is Friday at 09:00. That is close enough in time that I would be surprised if the two were unrelated.

The problem is that `rotate_key()` in `src/auth/keys.py:31` appears to do the safe thing. It reads the current key into `previous`, writes the new key to `current`, and keeps the old one under `previous`, which is what the comment claims and what would let existing sessions survive a rotation. So the obvious story, that rotation invalidates live sessions, is not supported by the function itself. Either the failure is elsewhere in the path, or the correlation is coincidental and something else also runs Friday morning.

Three things I did not check that could close the gap:

- The verification side. I only read the rotate function, not the code that validates an incoming session token. If it never consults `store.get("previous")`, or only consults it for some token versions, the old key being retained buys nothing.
- Atomicity and propagation. Between `store.set("current", new)` and `store.set("previous", previous)` there is a window where the old key is reachable under neither name. If app instances also cache the key in memory, some instances could be on the new key while others are still on the old one, for as long as the cache lives.
- Whether the token identifies which key signed it. Without a key id, verification has to try both keys, and I have not confirmed it does.

Two parts of the data also argue against a clean single-cause story. The Friday 09:00 spikes account for well under half of the events, so roughly 90 sign-outs in August happened at other times and need their own explanation, including a secondary bucket of 9 at 2026-08-14T13. And the device split is heavily mobile, 105 of 147 from android and iphone against 42 from desktop browsers, which a server-side key rotation would not obviously produce. That skew may just reflect your traffic mix, which I did not measure.

The next step that would actually settle it is reading the token verification path and confirming whether `previous` is ever used, then pulling the full log lines for a handful of the Friday 09:00 events to see whether those users' tokens were issued before the preceding rotation. Until that is done, the Friday timing is a lead and not a diagnosis.