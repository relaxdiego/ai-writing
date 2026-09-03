I didn't find the cause. Here's what I have and what I'd check next.

**What the data rules out.** The short runs aren't partial failures — they're ~half the rows *and* ~half the wall-clock (≈7 min / ≈23k rows vs ≈15 min / ≈48k). Every run is marked `ok`, and the write loop in `jobs/nightly_rollup.py:23` is wrapped in a single transaction, so a mid-run crash would roll back to zero rather than land half. That points upstream: the job is being handed about half the input, not losing half the output. `fetch_events` and the window are the place to look, not `write_rollup`.

**The one lead worth chasing.** In the 8 runs I pulled, the low ones fall on Aug 23, 26, and 29 — an exact 3-day spacing, which doesn't line up with day-of-week. I don't have an explanation for a 3-day period, and 3 points is thin evidence for a cycle. There are 30 rows in `job_runs`; I only looked at 8, so the first thing to do is pull all 30 and see whether the spacing holds or whether I pattern-matched noise.

**The thing I'd inspect.** `jobs/scheduler.py:61` sets `window_start = last_success_at or (now - timedelta(hours=24))`. I never traced where `last_success_at` is written or what it's derived from. If it can be stale, reset, or set from a different run's timestamp, the window shrinks and everything above follows. I also never read `fetch_events` itself, and never checked whether raw event volume in the source table actually dips on those dates — if it does, the job is behaving correctly and the problem is further upstream still.

Neither commit in `git log -- jobs/` looks related, and both predate the pattern as far as I can tell, though I didn't check their dates against the run history.

Want me to pull the full 30 runs and trace `last_success_at`?