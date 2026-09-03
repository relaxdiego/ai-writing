I did not find the cause. Here's what the data does and doesn't support.

## The one strong signal

The sign-outs cluster hard on Friday mornings at 09:00:

| Bucket | Count |
|---|---|
| 2026-08-07T09 | 14 |
| 2026-08-14T09 | 19 |
| 2026-08-21T09 | 16 |
| 2026-08-28T09 | 7 |

Those four dates are all Fridays, and `deploy/cron.d/rotate-session-keys` runs `0 9 * * 5` — 09:00 every Friday. That's 56 of 147 August events landing in the hour the session key rotates. It is not a coincidence I can explain away.

Two supporting negatives: the events span android (61), iphone (44), chrome-desktop (31) and safari-desktop (11) roughly in proportion to normal traffic, which argues against a client-side or single-platform bug; and `SESSION_LIFETIME` is 14 days, which doesn't produce a weekly pattern, so ordinary expiry isn't it.

## Why I stopped short of calling it the cause

`rotate_key()` in `src/auth/keys.py:31` deliberately preserves the old key:

```python
previous = store.get("current")
new = generate_key()
store.set("current", new)
store.set("previous", previous)
```

So on the face of it, rotation should *not* sign anyone out — which is exactly what the comment claims. I never read the verification path, so I don't actually know that it falls back to `previous` on a failed decode. The comment asserts the invariant; I didn't confirm the code honors it. Until someone reads that path, "rotation logs people out" is a correlation with no mechanism.

The correlation also doesn't cover everything. 91 of the 147 events are outside those Friday-09:00 buckets, including 9 at 2026-08-14T13 — same day as the biggest spike, four hours later. Something else is producing sign-outs too, or the rotation effect has a tail I don't understand.

One caveat on my own numbers: the hourly histogram used `uniq -c` without a preceding `sort`, so it counts contiguous runs. Log lines are time-ordered so same-hour entries should be adjacent and the counts should be right, but I didn't verify that.

## What I'd check next, in order

1. **The verify path.** Does session decoding actually retry with `store.get("previous")`? If it doesn't, that's the whole answer and the comment is simply wrong.
2. **How many hosts run that cron.** This is my leading hypothesis. If `rotate-session-keys` is installed on every app host and they share one key store, several rotations fire at 09:00 Friday. Each one shifts `current` into `previous` and discards the old `previous` — so after the second rotation, the key that signed a user's session is gone entirely, even with a correct fallback. That would hit a *small* subset of users (those whose sessions were signed with the now-evicted key) while leaving everyone else fine, and it would be invisible to you on a single-host dev setup. Testable by counting hosts with the cron file and checking whether the store shows more than one rotation per Friday.
3. **Whether rotation can fire off-schedule** — manual runs or deploy hooks — which could account for the 2026-08-14T13 cluster.

If you can tell me whether the app runs on more than one host, that narrows this quickly.