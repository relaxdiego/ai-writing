I didn't find a definitive cause, but the failure isn't random: the short runs fall on a three-day cycle.

In the last eight runs, Aug 23, 26 and 29 all wrote roughly 22–24k rows in about seven minutes, while Aug 24, 25, 27, 28 and 30 wrote roughly 48k in about fifteen. That's three points on the pattern, not enough to call it confirmed, and I only pulled eight of the thirty rows available in `job_runs`. A three-day period is worth noting because it matches no calendar cycle. If short runs landed on weekends or Mondays I'd look for a business-volume explanation; a period of three days points instead at something with its own rhythm, such as a partition or retention job, an upstream loader, or a cache that expires on a timer.

The duration is the most useful clue. The run takes half as long as well as writing half as much, which means `fetch_events` returned about half the events rather than the write loop dropping them. That rules out the theory I started with, a partial write or an aborted transaction in the loop at `jobs/nightly_rollup.py:23`, since a transaction that failed midway would still have spent the full time fetching and grouping. Every short run is also recorded as `ok`, so nothing is raising.

That leaves the window as the leading suspect. `jobs/scheduler.py:61` computes `window_start = last_success_at or (now - timedelta(hours=24))`, and on its face this is safe: consecutive windows abut, so no interval goes unread. It stops being safe if `last_success_at` is advanced by something other than a completed run of this job, or advanced before the run finishes, in which case a window would open partway through the period it was meant to cover. I did not trace where that column is written, and that's the gap I'd close first.

Three other things I left unchecked:

- The contents and dates of `9d02e1e` ("retry transient fetch errors"), which touches exactly the code path the evidence implicates, and whether its landing date lines up with the onset of the pattern.
- The remaining 22 rows in `job_runs`, to confirm the three-day cadence holds and find where it began.
- The raw event count in the source table for a short window against a long one, which separates "the job read less" from "there was less to read."

The last of those is the cheapest and the most decisive: if the source genuinely holds half as many events in those windows, the job is behaving correctly and the problem is upstream of this repository entirely.