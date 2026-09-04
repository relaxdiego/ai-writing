I didn't find the cause. What I did find is a timing correlation strong enough to be the first thing you check, plus a mechanism in the key-rotation code that would fit it — but I have not confirmed the two are connected.

The sign-outs cluster on Friday mornings:

| Hour bucket | "session expired" lines |
|---|---|
| 2026-08-07T09 | 14 |
| 2026-08-14T09 | 19 |
| 2026-08-21T09 | 16 |
| 2026-08-28T09 | 7 |
| 2026-08-14T13 | 9 |

Those four 09:00 buckets are all Fridays, and `deploy/cron.d/rotate-session-keys` is `0 9 * * 5` — Friday at 09:00. That covers 56 of the 147 events in the August log. The other 91 are scattered, and the 13:00 cluster on Aug 14 is its own thing that this doesn't explain at all.

The mechanism that would fit is in `src/auth/keys.py:31`. `rotate_key()` keeps exactly one old key: the new key becomes current, the outgoing current becomes previous, and whatever was previous is dropped. With weekly rotation that gives any signing key a two-week window of validity at most, but `SESSION_LIFETIME` in `src/auth/config.py:8` is 14 days with `remember_me = True`. A session issued shortly after one rotation is signed with a key that gets discarded two rotations later, while the session itself still has days of lifetime left. That would sign out precisely the users whose session is between roughly seven and fourteen days old when the cron fires — a minority at any single rotation, and never you, because a session you use daily gets re-issued long before it ages into that window. It also fits the client skew: android and iphone are 105 of the 147, and those are the clients that sit on a long-lived remember_me cookie for weeks.

Three things stand between that and an actual diagnosis, in the order I'd check them. First, timezone: the log timestamps look like UTC and cron runs in server-local time, so if those differ the Friday-09:00 alignment is coincidence and the whole line of reasoning goes away. Second, the verification path — I read `rotate_key()` but not the code that validates an incoming session, so "previous is also accepted" is an assumption I took from the comment rather than something I confirmed. Third, and this is the test that would settle it, whether any actually-signed-out session was 7 to 14 days old at the moment it failed. The lines I grepped carry a client string and a timestamp but no session issue time, so that check needs either a different log field or a query against the session store.