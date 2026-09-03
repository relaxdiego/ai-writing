I didn't find a definitive cause. Here's what I established and where I'd look next.

**What the data shows**

The runs are cleanly bimodal — there's no gradual degradation, just two distinct modes:

| | rows | duration |
|---|---|---|
| normal | 47.7k–48.4k | ~15 min |
| short | 22.1k–23.9k | ~7 min |

Duration scales with row count, so the job isn't being cut off partway — it does less work and finishes early, believing it succeeded. Every run in the sample is `status = ok`, including the short ones. That rules out the retry path in `9d02e1e` swallowing an error and marking the run failed, and it means nothing in the job considers a 23k-row night abnormal.

In the 8 runs I looked at, the short ones fall on Aug 23, 26, and 29 — exactly every third day, which doesn't line up with day-of-week or anything else I could see in `jobs/`. It may be coincidence over a small sample; only 30 runs exist in `job_runs` total, so I'd want the full set before treating the cadence as real.

**Where I'd look**

`jobs/scheduler.py:61` is my main suspicion, and I want to be clear it's a hypothesis I did not confirm:

```python
window_start = last_success_at or (now - timedelta(hours=24))
```

Roughly half the expected rows is what you'd get from roughly half the expected window. If `last_success_at` is sometimes written with a value later than the previous run's intended boundary, the next window opens short and the missing events are simply never scanned. That would also explain the clean bimodality and the `ok` status. But I never traced where `last_success_at` is written, so this is a shape-matches argument, not a finding — the "every third day" spacing doesn't obviously follow from it either.

The other candidate I couldn't rule out is `fetch_events` itself — a pagination cap or a `LIMIT` that trips under some condition would produce the same signature. I didn't read that function.

**What would settle it**

1. Log `window_start` and `window_end` on every run, or persist them as columns on `job_runs`. One short night with its window recorded would confirm or kill the scheduler hypothesis immediately.
2. Trace where `last_success_at` is written and whether it can be set from a finish time, a partial run, or a concurrent run.
3. Read `fetch_events` for a row cap or pagination loop.
4. Pull all 30 runs rather than 8, to see whether the 3-day spacing holds.

If you want, I'll do 2 and 3 now — both are read-only and would narrow this without waiting for another night's data.