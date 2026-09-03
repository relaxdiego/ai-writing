I didn't find the cause. Here's what I have.

The short-run days are real and they're not random: the last eight runs split cleanly into ~48k rows in ~15 minutes and ~22–24k rows in ~7 minutes. Roughly half the rows, roughly half the runtime, and status `ok` every time. That pattern says the job is being handed a smaller window rather than failing partway through a normal one — a crash or partial write would more likely leave a truncated run with the full duration or a non-ok status.

That points at the window calculation in `jobs/scheduler.py:61`:

```python
window_start = last_success_at or (now - timedelta(hours=24))
```

If a run's `last_success_at` is written at *finish* time rather than start time, or if two runs land close together, the next window covers less than 24 hours. A ~12-hour window would produce almost exactly what the short days show. But I did not verify this — I never looked at where `last_success_at` is set, and I didn't check the short-run dates against anything (a second scheduler instance, a DST or timezone boundary, a manual re-run) that would explain why it's some nights and not others.

What would settle it:

1. Find where `last_success_at` is written and whether it uses start or finish time.
2. Log or record the actual `window_start`/`window_end` per run — right now `job_runs` doesn't store them, so every diagnosis is inference from row counts.
3. Check whether the short nights correlate with anything: extra rows in `job_runs` for the same date, another scheduler process, or a specific weekday.

The two commits in `jobs/` are a base-image bump and a fetch retry; neither obviously touches windowing, though the retry commit is worth reading if `fetch_events` can return early on a swallowed error.