I didn't find the cause. Here's what I have.

The short runs are real and they cluster. On the last 8 runs, the low ones (Aug 23, 26, 29 — ~22–24k rows) all finished in 6–7 minutes; the normal ones (~48k rows) all took 15–16 minutes. So the job isn't failing partway and truncating — it's doing roughly half the work and completing cleanly, status `ok` each time. That points at input, not output: `fetch_events` is returning about half the events on those nights.

The most suspicious thing I saw is the window calculation in `jobs/scheduler.py:61`:

```
window_start = last_success_at or (now - timedelta(hours=24))
```

The window starts at the *last success*, so if anything ever runs off-schedule or the recorded success timestamp drifts forward, the next window is correspondingly shorter and the job legitimately sees fewer events. That's consistent with a clean `ok` and a short runtime. But I did not confirm it — I never compared `window_start`/`window_end` against `last_success_at` for a short run, and the `job_runs` rows I pulled don't include the window bounds, so I can't tell whether the short nights actually had short windows.

The other thing I noticed but didn't chase: the low runs are Aug 23, 26, 29 — every third day. A three-day period doesn't obviously fall out of a "window starts at last success" bug, which would drift rather than repeat on a fixed cycle. That may be coincidence over only 8 data points, or it may mean something else entirely (a competing job, a partitioned source, a rotating replica). I didn't investigate it.

To settle it, the cheapest next step is to log or query the actual `window_start` and `window_end` per run and check them against the row counts — if the short nights have ~12-hour windows, it's the scheduler line; if they have full 24-hour windows, the problem is inside `fetch_events` and the every-third-day pattern is worth taking seriously. I'd also pull all 30 `job_runs` rows rather than 8, to see whether the periodicity holds up.