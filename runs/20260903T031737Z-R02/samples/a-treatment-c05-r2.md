I didn't find a definitive cause. Here's what the evidence narrows down and what I'd check next.

The shortfall isn't random. In the last eight runs, three came in at roughly half volume — Aug 23 (23,551), Aug 26 (22,104), Aug 29 (23,902) — against ~48,000 on the others, and each short run finished in about seven minutes versus fifteen. The short days are exactly three days apart, which is too regular for load noise and points at something on a cycle rather than an intermittent fault.

Two things argue that rows are missing on the way *in*, not being lost on the way out. Every run reports `ok`, and `jobs/nightly_rollup.py:23` wraps the entire write loop in one transaction, so a mid-run failure would roll the whole batch back rather than commit half of it; a half-size commit that also reports success is hard to produce from the write path. The proportionally shorter runtime says the same — the job wasn't interrupted partway, it had less work to do from the start.

I did chase the obvious window bug and it doesn't hold up on the data I have. `jobs/scheduler.py:61` derives `window_start` from `last_success_at` rather than a fixed offset, so an extra successful run mid-day would shorten the next window to ~12 hours and halve the output. But all eight rows I pulled are consecutive 02:00 runs with no off-cycle run before any of the short days, so unless something updates `last_success_at` outside `job_runs`, the window was a full 24 hours each time. My leading suspect instead is `9d02e1e "fix: retry transient fetch errors"` — a retry wrapper that swallows a failure and returns the pages it managed to collect would produce exactly this signature: fewer rows, normal runtime scaling, no error status. I have not read that diff, so treat it as a hypothesis rather than a finding.

Checks I'd run, in order:

1. **Read the `9d02e1e` diff and `fetch_events`** — specifically whether the retry path can return a partial result set without raising, and whether it logs anything on a swallowed error.
2. **Count source events per hour for Aug 29 against Aug 30** — separates "the data wasn't there" from "the job didn't read it," and shows whether the missing half is a contiguous time block (window/pagination) or spread evenly (upstream volume).
3. **Pull all 30 `job_runs` rows, plus `last_success_at` writes** — confirms the three-day period holds further back, dates when it started, and catches any off-cycle success I couldn't see in eight rows.

Worth flagging: `job_runs` only retains 30 rows, so I can't tell whether this predates the two recent commits to `jobs/`. If you can point me at older logs or the scheduler's own output for Aug 26, that would likely be faster than any of the above.