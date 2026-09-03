I didn't find the cause. Here's what I have.

The short-row nights are real and they cluster: the 8 runs I looked at split cleanly into ~48k rows taking ~15 minutes, and ~22–24k rows taking ~7 minutes. Aug 23, 26, and 29 are the short ones — three days apart each time, though three points isn't enough to call it a weekly pattern. Every run is marked `ok`, so whatever's happening isn't raising.

The thing that caught my eye is `scheduler.py:61`: the window start is `last_success_at or (now - timedelta(hours=24))`. That makes each run's window depend on the previous run's recorded success time, so a short window would produce proportionally fewer rows in proportionally less time — which matches the shape of the data. But I did not verify this. I never looked at what actually writes `last_success_at`, whether it's set to the run's start or finish, or whether anything else (a manual run, a backfill, a second scheduler instance) touches it. The halving is suspiciously clean for a window-drift explanation, and I have no story for why it would recur on a 3-day spacing. So treat this as the first place to look, not a diagnosis.

What I'd check next, roughly in order:

1. `select started_at, finished_at, status, rows_written from job_runs where job='nightly_rollup' order by started_at desc limit 30` — I pulled the count of recent runs but only read 8 of them. Thirty rows would show whether the short nights are actually periodic.
2. Log or query the computed `window_start`/`window_end` per run and compare against the 24h nominal. If the short nights have ~12h windows, that confirms it and points at `last_success_at`.
3. Find every writer of `last_success_at`, and check whether more than one scheduler instance or a manual invocation is running on those nights.

Two things I looked at and found nothing in: the `run()` body at `nightly_rollup.py:20-25` has no early return or row limit, and the only recent commits under `jobs/` are an image bump and a fetch-retry change — neither obviously related, though I didn't read the retry diff closely enough to rule it out.