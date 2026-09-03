I didn't find the cause. Here's what I have and what I'd do next.

**The clearest signal:** `rows_written` is bimodal, not randomly variable. Runs land at either ~48k or ~23k — there's nothing in between:

```
08-30  14m47s  48213
08-29   7m09s  23902   <-- short
08-28  16m28s  47881
08-27  15m00s  48440
08-26   6m55s  22104   <-- short
08-25  15m40s  48009
08-24  15m16s  47760
08-23   6m37s  23551   <-- short
```

The short runs also take about half the wall time. That matters: if the job were writing rows and losing them, runtime would stay flat. Halved runtime *and* halved output points at the job processing roughly half the input — the shortfall is most likely upstream of the write, in `fetch_events` or in the window it's given, not in `write_rollup`.

That's also consistent with the code shape: the writes are wrapped in a single `transaction()`, so a partial write should roll back entirely rather than commit half. And every one of these runs recorded `status='ok'`, so whatever is happening is not raising.

**What I could not establish:** why it happens on those particular nights. The three short runs fall on Aug 23, 26, and 29 — exactly three days apart. I want to flag that I noticed it and equally that I don't trust it: it's three data points, I only looked at the most recent 8 of 30 runs, and a 3-day cadence doesn't map to any schedule I found in the repo. It could easily be coincidence.

**My leading hypothesis, untested:** `9d02e1e "fix: retry transient fetch errors"` is the kind of change that produces exactly this signature — if the retry wrapper gives up after N attempts and returns whatever it collected instead of raising, the job would summarise a partial event set, commit cleanly, and report `ok`. I did not read that code, so this is a suspicion, not a finding. The competing explanation is that `window_start` is sometimes wrong: `last_success_at or (now - timedelta(hours=24))` is a shorter window if `last_success_at` is being written as the previous run's *finish* time, though that alone accounts for ~15 minutes of drift, not 12 hours.

**Cheapest next steps, roughly in order:**

1. Read `fetch_events` and the diff in `9d02e1e` — does any path return partial results without raising? This is a few minutes and either kills or promotes the main hypothesis.
2. Pull all 30 `job_runs` rows rather than 8, to see whether the bimodal split and the apparent cadence actually hold.
3. For one short night, count source events in that window directly and compare to `rows_written`. That definitively splits "fetched less" from "wrote less" and would let me stop guessing.

**The gap that made this hard:** `job_runs` doesn't record `window_start`/`window_end`. If it did, I could have answered this from the table alone. Logging those two values per run is worth doing regardless of what the cause turns out to be — and if the cause is window drift, it makes the next occurrence self-diagnosing.

Want me to go ahead with steps 1–3?