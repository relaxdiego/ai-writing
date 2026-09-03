I did not find the cause. What I have is a narrowing, plus the two checks that would settle it.

The short nights are real and they may have a shape. In the last eight runs the light ones are 23 August (23,551 rows), 26 August (22,104) and 29 August (23,902), against roughly 48,000 on the others: every third night. I only pulled eight of the thirty rows in `job_runs`, so that pattern rests on three points and could easily be coincidence. Pulling all thirty is cheap and worth doing before anyone builds a theory on a three-day cycle.

The stronger signal is that duration tracks rows. Light nights finish in about seven minutes, full nights in about fifteen. So the job is not failing partway and committing what it had; it is doing half the work in half the time and exiting with status `ok`. Since every write happens inside one transaction (`jobs/nightly_rollup.py:23`), a partial write would roll back rather than commit 22,000 rows. That puts the fault upstream of the write, in `fetch_events` or in the window handed to it.

Worth flagging separately: the loss is permanent, not deferred. `window_start` comes from `last_success_at` (`jobs/scheduler.py:61`), and a light run still records success, so the next night starts from that timestamp and covers its own 24 hours normally. The 27th wrote 48,440 after the 26th came up short. Nothing ever goes back for the rows the light nights missed.

My leading candidate is the retry in `9d02e1e`, "retry transient fetch errors". If that retry wraps a paginated or streaming fetch and returns whatever it has accumulated once attempts are exhausted, the job sees a short list and no exception, which is exactly half the rows, half the runtime, status `ok`. I did not read `fetch_events`, and that is the single highest-value thing still unread.

The alternative is the window itself. `last_success_at` carries no explicit timezone in the code I read, and `a3f81cc` bumped the scheduler base image, which can change the container's TZ or clock source. I rate this lower because an offset of that kind is usually constant, and this failure is intermittent.

The two hypotheses separate cleanly. Log `window_start`, `window_end` and `len(rows)` at the top of `run()`, then compare a light night against a full one. A full 24-hour window with half the rows is a fetch bug. A window that is itself short is the scheduler.