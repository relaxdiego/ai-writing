## Bottom line

I did not find the cause. I found a clear, reproducible *signature* of the failure, but I stopped short of anything I'd call a diagnosis — the evidence I gathered is consistent with at least three different root causes and I didn't do the work to separate them.

## What the data actually shows

The last 8 runs are cleanly bimodal — not a gradual shortfall:

| date | duration | rows |
|---|---|---|
| 08-30 | 14m47s | 48213 |
| 08-29 | **7m09s** | **23902** |
| 08-28 | 16m28s | 47881 |
| 08-27 | 14m58s | 48440 |
| 08-26 | **6m55s** | **22104** |
| 08-25 | 15m40s | 48009 |
| 08-24 | 15m16s | 47760 |
| 08-23 | **6m37s** | **23551** |

Two things worth noting:

- **Duration scales with rows.** The short runs aren't stalling or timing out — they're doing about half the work and finishing cleanly. That argues against a crash/partial-write inside the loop, and toward the job simply being *handed* half the input.
- **Every run is `status = ok`.** Whatever goes wrong is invisible to the job itself, which is why it's gone unnoticed.

The three bad nights are 08-23, 08-26, 08-29 — every third day. I want to flag this as a *possible* red herring: I only pulled 8 of the 30 available rows, so with three data points a 3-day spacing could easily be coincidence. It's cheap to confirm or kill and I'd do that first.

## Hypotheses, none confirmed

1. **The window is short on bad nights.** `scheduler.py:61` computes `window_start = last_success_at or (now - timedelta(hours=24))`. Half the rows in half the time is exactly what a ~12h window would look like. But I never checked what writes `last_success_at`, or whether it's set to the run's *start* or *finish* time, so this is inference from shape alone.
2. **Upstream data is late.** If the source table isn't fully loaded at 02:00 on some nights, `fetch_events` takes what exists and the job reports success. This fits the evidence just as well as (1) and would mean the bug isn't in this repo at all.
3. **The retry commit swallows a partial fetch.** `9d02e1e "fix: retry transient fetch errors"` is suspicious given the symptom — a retry path that returns a partial result and continues would produce exactly this. **I did not read that diff.** In hindsight that was the obvious next move and I should have done it before writing up.

## What I did not check

Being explicit, since it bounds how much the above is worth:

- The diffs of either commit touching `jobs/`
- The bodies of `fetch_events`, `group_by_account`, `summarise`, `write_rollup` — I only read `run()`
- What sets `last_success_at`
- Rows 9–30 of `job_runs`
- Whether runs ever overlap or double-fire
- Any application logs from a bad night
- Timezone/DST behavior around the 02:00 trigger

## Suggested next steps

The single biggest gap is that **`job_runs` doesn't record the window it processed**, so every question above is unanswerable after the fact. I'd add `window_start` / `window_end` columns before anything else — one bad night with that logged likely settles it outright.

Cheap checks, in order:

```bash
git show 9d02e1e                      # does the retry path return partial results?
psql -c "select started_at, finished_at, rows_written from job_runs \
         where job='nightly_rollup' order by started_at desc limit 30"   # is the 3-day cadence real?
```

Then, to test hypothesis 2 independently of the job: count source events directly for a known-bad window and compare against a good one. If the source is short, the job is behaving correctly and the problem is upstream.

Happy to run any of these — I'd start with the `git show`.