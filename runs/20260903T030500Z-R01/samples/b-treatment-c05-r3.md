I didn't find the cause. Here's what I have and what I'd check next.

**The pattern is real and bimodal.** Of the last 8 runs, five wrote ~48k rows in ~15 minutes, three wrote ~22-24k in ~7 minutes. It's not a gradual degradation — runs land in one bucket or the other, and the short runs write roughly half the rows in roughly half the time. Short runs are 08-23, 08-26, 08-29: every three days, though 8 data points is too few to call that a real period. All runs report status `ok`, so nothing is erroring out.

**The most suspicious thing I saw** is `jobs/scheduler.py:61`:

```python
window_start = last_success_at or (now - timedelta(hours=24))
```

The window starts at the last successful run's timestamp rather than a fixed 24-hour boundary. If a run ever starts from a `last_success_at` that's more recent than it should be — an extra run, a manual trigger, a backfill, a retry that updated the timestamp — the next window is short and picks up fewer events. That would produce exactly this shape: fewer rows, proportionally less work, clean exit. But I did not verify it. I never looked at what `last_success_at` actually was on the short runs, and the `job_runs` rows I pulled don't include the window bounds, so this is a hypothesis fitted to the symptom, not a finding.

**What would settle it:**

1. Query `job_runs` for the window bounds on the short runs, if they're recorded. If not, log `window_start`/`window_end` and the `fetch_events` row count on every run — one line, and the next short run tells you whether the input was short or the processing dropped rows.
2. Check whether anything other than the 02:00 cron writes `last_success_at`. The full `job_runs` table (30 rows) would show extra or off-schedule entries; I only pulled 8.
3. Compare `rows_written` against the raw event count for a short night. If the input window was full-length and the output was still half, the problem is downstream in `group_by_account`/`write_rollup`, not the window.

**What I ruled out weakly:** the two commits touching `jobs/` are a base image bump and a fetch retry addition. Neither obviously causes this, but `9d02e1e` (retry transient fetch errors) is worth reading closely — a retry that swallows a partial failure and returns a short result set would also fit, and it interacts with the `last_success_at` logic if a retried run updates that timestamp.