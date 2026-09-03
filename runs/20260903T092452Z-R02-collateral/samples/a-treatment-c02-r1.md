Your skepticism is reasonable, but not because pool exhaustion is unlikely. It's a plausible cause; the problem is that at least six other failure modes produce exactly the same symptom, and none of them can be told apart by reasoning about the symptom. The fix is to make the next hang produce a stack dump instead of a dead job.

Before anything else, check whether "always a different test" is actually true. Under CI, stdout is a pipe rather than a terminal, so the runner's output is block-buffered and the last line you see is not the last test that started. If the harness only prints a test's name on completion, the reported location is systematically wrong. Turn on unbuffered output and per-test start and finish timestamps so you know the true position. This matters because the position within the run is itself evidence: a steady resource leak exhausts the pool at a fairly predictable point, so hangs cluster in the back half of the suite, whereas a race or a lost wakeup lands uniformly. A leak down a rare error path also lands uniformly, so a random position weakens the plain version of the pool hypothesis without killing it.

The unifying feature of everything below is a wait with no deadline. Whatever the underlying flake is, it almost certainly happens far more often than one run in twenty; you only notice the occasions when it lands on a wait that nothing bounds.

- **Pool or handle exhaustion.** Connections leaked on error paths, never returned, and an acquire call with no timeout. Includes HTTP client sockets and file descriptors, not just the database pool.
- **Database lock contention.** A test dies mid-transaction, leaves a session idle in transaction holding a row or table lock, and a later test's `TRUNCATE` or migration blocks behind it forever. From the outside this is indistinguishable from pool exhaustion, and it's arguably more common.
- **Subprocess pipe deadlock.** A test spawns a process, waits for it to exit, and doesn't drain its stdout. The child fills the 64KB pipe buffer and blocks writing; the parent blocks waiting for exit. Locally the child is often chattier or quieter, or output goes somewhere else, so it never trips.
- **Lost wakeup or dead producer.** A `queue.get()` or future that nothing will ever complete, because the background task that would complete it raised and died silently, or the event fired before the waiter registered. CI's different timing flips the interleaving.
- **Core count and worker starvation.** Runners typically have two cores against your eight or sixteen. A blocking call on the event loop, or a pool sized from CPU count where a test needs one more worker than exists, deadlocks only on the small machine.
- **Cross-job interference.** If concurrent pipeline runs share a database, a Redis, or an advisory lock namespace, another branch's job blocks yours. This fits "never locally" perfectly, and a one-in-twenty rate tracks how often two jobs overlap.
- **Post-suite hang.** The tests all finished and a non-daemon thread, a coverage merge, or a reporter is keeping the process alive. Looks like a hang "at" whichever test printed last, which is to say at a different test every time.

To discriminate, capture a full thread dump at the moment of the hang. Set a watchdog inside the job that fires comfortably before the CI platform's own timeout, because if the platform kills the job first you get nothing. In Python, `faulthandler.dump_traceback_later(600, exit=True)` costs one line, or attach `py-spy dump --pid`; for the JVM send `SIGQUIT` or run `jstack`; for Go send `SIGABRT`; for Node use the inspector via `SIGUSR1`. That single artifact separates nearly every hypothesis above at a glance, since it tells you whether you are parked in pool acquire, in a socket read, in `waitpid`, in a queue wait, or in a futex.

Have the same watchdog dump the surrounding state before it exits, and upload it as a job artifact:

```bash
ss -tanp                                  # socket states; count ESTABLISHED to the DB
ls /proc/$PID/fd | wc -l                  # fd growth
psql -c "select pid, state, wait_event_type, wait_event, xact_start, left(query,80)
         from pg_stat_activity order by xact_start"
psql -c "select pid, mode, granted, relation::regclass from pg_locks where not granted"
```

Exactly `pool_max` connections all sitting in `idle in transaction` is the pool story. One ungranted lock with a blocker holding it is the lock story. A handful of established sockets and everything parked in `waitpid` is the subprocess story.

Two cheap experiments are worth running regardless of what the dump shows. Set a finite acquire timeout on the pool, plus `lock_timeout` and `statement_timeout` on the database session, and you convert the hang into a fast failure with a stack trace that names the offending test; this both tests the hypothesis and defuses the worst of it. Then add a job that runs the integration suite twenty times in a loop, or twenty copies in parallel, so you get a reproduction within the hour instead of waiting a week for the next natural occurrence.

For a local reproduction, match the runner rather than your laptop: run the suite inside the CI container image, under `taskset -c 0,1` with the runner's memory limit, with output redirected to a file rather than a terminal, and with the same worker count and the same test ordering seed. If serializing the integration suite makes the hang disappear, the cause is concurrency or shared state and the list narrows to the last three entries. If giving each CI job a uniquely named database drops the rate to zero, it was never your code at all.