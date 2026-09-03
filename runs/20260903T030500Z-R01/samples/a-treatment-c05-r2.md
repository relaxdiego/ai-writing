I didn't find the cause. Here's what the evidence does and doesn't support.

**The failure isn't random.** The last 8 runs fall into two clean clusters, not a spread:

- full: ~48k rows, ~15 min (Aug 24, 25, 27, 28, 30)
- short: ~22–24k rows, ~7 min (Aug 23, 26, 29)

Every run reports `status = ok`. Nothing is erroring.

**Runtime halves in proportion to rows.** This is the most useful signal. If the job were fetching a full window and losing rows on the write side — a partial commit, a swallowed exception in the loop, a key collision in `write_rollup` — it would still spend the full ~15 minutes doing the fetch and grouping work. It doesn't. The short runs are doing about half the *work*, which points at `fetch_events` returning about half the input, not at the transaction or the write path.

**Two candidates, neither confirmed:**

1. `scheduler.py:61` — `window_start = last_success_at or (now - timedelta(hours=24))`. This is the only input to the job that varies. If `last_success_at` is ever written as something other than the prior `window_end` (the finish timestamp, say, or a value from a differently-scoped query), the window would narrow. But I haven't read where `last_success_at` is set, so this is a guess about the shape of the bug, not a finding.
2. `9d02e1e fix: retry transient fetch errors`. A retry wrapper that exhausts and returns a partial result instead of raising would produce exactly this: less input, shorter runtime, `status = ok`. I didn't read the diff.

**The cadence is suspicious but underpowered.** The short runs land on Aug 23, 26, 29 — three days apart. I only pulled 8 rows, so that's three data points and could easily be coincidence. Worth confirming against all 30 before reading anything into it.

**What I'd do next, in order:**

- Pull all 30 rows including `window_start`/`window_end` if those columns exist. If the short runs have visibly narrower windows, it's the scheduler and the cadence is a red herring.
- If the windows are identical width, count source events in that window directly (`select count(*) from events where ts between ...`) for one short run and one full run. That decides input-truncation vs. window-narrowing outright.
- Read `9d02e1e` and whatever sets `last_success_at`.

The second step is the one that actually splits the hypotheses; I'd start there if you only have time for one.