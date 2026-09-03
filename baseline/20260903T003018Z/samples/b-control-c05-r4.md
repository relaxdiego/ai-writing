I didn't find the cause. Here's what I have, and what I'd check next.

**What the data shows**

The short runs aren't partially-failed long runs — they're genuinely doing less work. Every low-row run finished in ~7 minutes; every normal run took ~15. All eight are marked `ok`. So the job isn't dying halfway through the write loop; it's being handed roughly half the input and processing it happily.

The affected dates in the window I looked at are 8/23, 8/26, 8/29 — exactly three days apart. That's a striking pattern and I don't have an explanation for it. It's also based on only 8 rows; I pulled the count (30 runs available) but never actually looked past the most recent 8, so I can't say whether the cadence holds historically or is a coincidence in a small sample.

**Leads I did not run down**

- *`fetch_events` itself.* I never opened it. Given the symptom is "less input, not failed output," this is where I'd start. The recent commit `9d02e1e "fix: retry transient fetch errors"` is suspicious in exactly this way: if the retry wrapper catches an error mid-pagination and returns the pages accumulated so far instead of re-raising, you'd get a silent short read that looks like a clean success. That's a guess about code I haven't read, not a finding.
- *The window calculation.* `window_start = last_success_at or (now - timedelta(hours=24))` caught my eye, but I couldn't make it produce a halving — successful runs finish around 02:15, so the window comes out near 23.75h either way. It's only a real suspect if `last_success_at` is sometimes written with a different timezone or is set by a *different* job that also writes to `job_runs`. I didn't check either.
- *Upstream volume.* I never verified that the source table actually contains ~48k events' worth of data on the short nights. If the events simply aren't there at 02:00, the bug is in whatever produces them, and everything above is the wrong tree.

**What would settle it fastest**

Run `select count(*) from events where created_at between <window> ` for one good night and one bad night. That single comparison splits the problem cleanly: if the counts match, the bug is in `fetch_events`/retry; if the bad night is genuinely half-empty, the nightly job is innocent and the problem is upstream. Everything else I'd do depends on that answer.