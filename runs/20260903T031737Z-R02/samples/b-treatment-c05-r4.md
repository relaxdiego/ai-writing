I didn't find the cause. Here's what I have, and what I'd check next.

The runs split cleanly into two populations rather than varying continuously. Full runs write ~48k rows and take ~15 minutes; short runs write ~22–24k and take ~7 minutes. In the eight runs I pulled, the short ones fall on Aug 23, 26 and 29 — exactly three days apart, and every run is recorded `ok` with no failure or retry visible in `job_runs`. Because duration scales with row count, the job is doing about half the *work* on those nights, not writing half of what it fetched. That points upstream at `fetch_events` or the window it's given, and away from the write path and the transaction in `run()`.

One thing I want to flag before you anchor on the framing: the data doesn't actually tell us which population is wrong. If ~24k is the true daily volume, then the 48k runs are the anomaly and something is causing them to cover roughly two days of events. `window_start = last_success_at or (now - timedelta(hours=24))` is exactly the kind of expression that produces a doubled window when `last_success_at` is stale, null, or written from a different clock than `now`. I couldn't distinguish the two readings from row counts alone — it needs a check against the source table for what a single day actually contains.

The other open lead is `9d02e1e "fix: retry transient fetch errors"`. I never read that implementation. If the retry path can return a partial result and still report success — swallowing a truncated page, or restarting a paginated fetch without resuming — it would produce precisely this signature: short duration, halved rows, status `ok`. I also didn't check when that commit landed relative to the first short run, which is the cheapest way to promote or drop it as a hypothesis.

Concretely, what I'd do next:

- `git log --format='%h %ad %s' -- jobs/` and compare the dates of `9d02e1e` and `a3f81cc` against the onset of the pattern.
- Pull all 30 rows from `job_runs`, not the 8 I looked at, to confirm the three-day period is real and not coincidence in a small sample.
- Count events directly in the source table for one short-run window and one full-run window, which settles whether 24k or 48k is the correct daily figure.
- Read `fetch_events` and the retry wrapper for any path that returns early or resets pagination on a retry.
- Check `last_success_at`: whether it's set from `started_at` or `finished_at`, and whether it and `now` share a timezone. A three-day beat is odd for DST, but a scheduler running more than one instance since the image bump in `a3f81cc` could produce it, with concurrent runs stealing each other's window.

Things I can't get from the repo: scheduler logs for the short nights, the deployment history around `a3f81cc`, and whether more than one scheduler replica is live. If you can hand me any of those, or just run the first three checks above, I think this narrows quickly.