I didn't find the cause. Here's what the evidence does and doesn't support.

The short runs aren't losing rows at the end — they're doing half the work from the start. Aug 23, 26, and 29 each wrote ~23k rows in ~7 minutes, against ~48k rows in ~15 minutes on the full runs. Duration scales with the row count, which points upstream at `fetch_events` or the window it's given, not at the transaction or the write path. All three are logged `ok`, so no error branch is being taken; that also makes the recent `fix: retry transient fetch errors` commit an unlikely culprit, though I didn't read it.

The three short runs in the last 8 fall on a 3-day spacing. I only pulled 8 of the 30 rows available, so I can't tell you whether that holds — it may be coincidence in a small sample.

The thing I'd check first is `last_success_at` in `jobs/scheduler.py:61`. A short window would produce exactly this shape (less data fetched, proportionally less time), and whether that value is the previous run's `started_at` or its `finished_at` changes the window by the ~15 minutes the job takes. That alone doesn't explain a halving, but it's the only input to the window and I never traced where it's written.

To get to an answer:

- Pull all 30 `job_runs` rows and check whether the 3-day spacing is real.
- Log `window_start`/`window_end` per run, or recover them if they're already persisted — that settles in one night whether the window is short or the window is fine and `fetch_events` is returning less for it.
- Read `fetch_events` and `group_by_account`. I read neither; a `LIMIT`, a partitioned source, or a silent dedup in grouping would all produce this and none would show up in what I looked at.

If you can share a short run's actual window bounds, that should narrow it quickly.