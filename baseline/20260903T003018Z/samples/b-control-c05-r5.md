# Nightly rollup: no definitive cause yet

I didn't find the cause. Here's what I did find, and what I'd check next.

## What the data shows

The "half rows" runs are real and they're not random — they cluster into two clean groups:

| Date | Duration | Rows |
|---|---|---|
| 08-30 | 14m47s | 48,213 |
| 08-29 | **7m09s** | **23,902** |
| 08-28 | 16m28s | 47,881 |
| 08-27 | 15m58s | 48,440 |
| 08-26 | **6m55s** | **22,104** |
| 08-25 | 15m40s | 48,009 |
| 08-24 | 15m16s | 47,760 |
| 08-23 | **6m37s** | **23,551** |

Two observations worth more than anything I found in the code:

1. **Short runs are proportionally short.** ~7 minutes for ~half the rows, ~15 minutes for full rows. The job isn't being cut off partway — it processes less input and finishes early and cleanly. That points at the *input window*, not at the write path, the transaction, or a timeout.
2. **Every run is marked `ok`.** Nothing is erroring. Whatever's happening looks like normal operation to the job.

The bad dates are Aug 23, 26, 29 — a 3-day spacing. That's suggestive but I want to be honest: three points over 8 days is weak evidence. It could be a genuine every-third-day cycle, or coincidence in a small sample.

## Where I'd look, and why

`jobs/scheduler.py:61` computes the window as:

```python
window_start = last_success_at or (now - timedelta(hours=24))
window_end = now
```

The window is anchored to `last_success_at`, so it's *self-adjusting*: if a run starts late, the next window is shorter. That's the kind of mechanism that produces exactly what we see — a shorter window, less input, a proportionally faster run, no error. But I did not confirm it, and there's a real problem with the theory: the `started_at` values are all within a couple of seconds of 02:00, so nothing is visibly starting late in the rows I pulled. Either the mechanism is different, or `last_success_at` diverges from `started_at` in a way I haven't traced.

I also didn't rule out the simplest explanation: **the source data may genuinely be half-sized on those days.** A half-row output is the correct output for a half-sized input. I never looked at the event volumes themselves, so this remains fully open, and it would explain the numbers just as well.

## What I did not check

- The actual value of `last_success_at` per run (I only inferred from `started_at`)
- Source event counts per day — the obvious control, and the biggest gap
- How `last_success_at` is written, and whether retries (`9d02e1e`, "retry transient fetch errors") update it
- Whether `a3f81cc`, the scheduler image bump, changed timezone/DST behaviour in the container — it touches exactly the component that computes the window
- More than 8 runs; the table has 30, and the extra 22 would tell us whether the 3-day spacing is real

## Suggested next step

Two queries would likely settle it:

```sql
-- 1. Do the short runs correspond to short windows?
select started_at, last_success_at, finished_at, rows_written
from job_runs where job='nightly_rollup'
order by started_at desc limit 30;

-- 2. Or was there simply less input on those days?
select date_trunc('day', event_time) d, count(*)
from events where event_time > now() - interval '30 days'
group by d order by d;
```

If query 1 shows short windows on 8/23, 8/26, 8/29, it's the window logic. If query 2 shows low event counts on those days, the job is fine and the problem is upstream. Happy to run both if you can point me at a database I can query, or paste the output and I'll take it from there.