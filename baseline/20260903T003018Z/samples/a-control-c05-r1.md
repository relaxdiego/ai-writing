I didn't find a definitive cause. Here's what I established and where I'd look next.

**What the data rules out.** Every run reports `status = ok`, so this isn't a crash or a partially-committed transaction. The row counts are cleanly bimodal — roughly 48k or roughly 23k, nothing in between — and the short runs also take about half as long (7 min vs 15 min). That proportionality matters: the job isn't losing rows on the write side, it's doing about half the work. That points upstream at `fetch_events` and the window it's given, not at `write_rollup` or the transaction block.

**The lead I'd chase.** `scheduler.py:61` sets `window_start = last_success_at or (now - timedelta(hours=24))`. A window that's half the intended length would explain both the row count and the runtime. But I did not verify this — I never read the code that *writes* `last_success_at`, so I don't know whether it stores the run's start or finish time, how it handles timezones, or whether it can be stale or null. That's the gap between "plausible" and "the cause."

**A pattern I couldn't confirm.** In the 8 runs I pulled, the short days were 8/23, 8/26, and 8/29 — every three days. That's suggestive, but I only looked at 8 of the 30 available rows, so it may be coincidence.

Next steps, cheapest first:

1. Pull all 30 `job_runs` rows. If the 3-day cadence holds it's schedule-shaped; if it doesn't, that hypothesis dies for the cost of one query.
2. Log the actual `window_start`/`window_end` and the `fetch_events` row count per run, then compare against a direct count of source events in that interval. This distinguishes "wrong window" from "correct window, fewer events upstream."
3. Read the diff for `9d02e1e` ("retry transient fetch errors") — I never opened it, and a retry that swallows a partial fetch would produce exactly this signature.

Want me to run these?