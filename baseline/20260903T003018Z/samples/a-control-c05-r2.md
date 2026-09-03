I didn't find the cause. Here's what I have and what I'd check next.

**What the data shows**

The runs split cleanly into two clusters, not a continuum:

| | rows | duration |
|---|---|---|
| "full" runs (Aug 24, 25, 27, 28, 30) | ~47.8–48.4k | ~15 min |
| "half" runs (Aug 23, 26, 29) | ~22.1–23.9k | ~7 min |

The important part: **runtime halves along with the row count.** The job isn't doing full work and dropping output at the end — it's processing about half as many events from the start. That points upstream at `fetch_events` or the window, and largely rules out `write_rollup`, the transaction block, and `group_by_account` in `jobs/nightly_rollup.py:20-25`.

Every short run is also marked `ok`, so whatever happens is silent.

**Leads I couldn't close**

1. `9d02e1e fix: retry transient fetch errors` is my top suspect. If the retry wrapper catches an error mid-pagination and returns the partial batch instead of re-raising, you'd get exactly this: fewer rows, proportionally shorter runtime, status `ok`. I did not read that diff.
2. The window in `jobs/scheduler.py:61` is `last_success_at or (now - 24h)`. Since every run succeeds, that should stay contiguous — but if `last_success_at` is written from `finished_at` rather than `window_end`, or if a second unlogged instance consumed part of the window, coverage would have holes.
3. Thin but odd: the short runs are Aug 23, 26, 29 — every three days, which doesn't line up with day-of-week. Three data points, so I'd treat it as a hint, not a pattern.

**What would settle it**

- Read the retry code from `9d02e1e` — does it ever return a partial result set?
- Count source events per window directly for one short day and one full day. If the source count is also halved, it's the window or upstream data; if not, the job is dropping events.
- Check consecutive runs for window gaps or overlaps, and confirm nothing else writes `job_runs` for this job.

Want me to run those three? The first two should be decisive on their own.