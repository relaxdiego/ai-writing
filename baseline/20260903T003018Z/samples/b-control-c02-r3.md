## First, what "always a different test" actually tells you

That's the most informative thing in your description, and it rules out more than it looks like. It means the *test* isn't the cause — the test is just whoever was holding the bag when an ambient condition tripped. So stop looking for a bad test and start looking for state that accumulates or arrives from outside.

But "different test" splits into three sub-patterns with very different implications, and you probably already have the data to tell them apart in your existing CI logs:

- **Different name, roughly the same position in the run** (test #340 ± 10, whatever that happens to be) → something cumulative: a leak of connections, file descriptors, threads, or memory crossing a threshold. This is the pattern that would actually support the pool theory.
- **Different name, different position, but always the same shard/worker** → that worker's fixture, container, or connection is broken; the rest is noise.
- **Genuinely uniform in position** → nothing is accumulating. The trigger is external and time-based: a network event, a neighboring job, a runner-level stall.

If your test ordering is randomized, also grab the seed. If it isn't randomized, the "position" axis is still meaningful.

## Mechanisms that produce CI-only hangs

Grouped by the actual failure shape:

**Blocking wait with no timeout on something that occasionally never arrives.** This is my default suspicion for a hang (as opposed to a crash or a flake). A socket read with no `SO_TIMEOUT`, no TCP keepalive, and a peer that vanished silently. In containers this is common and near-impossible locally: NAT/conntrack entries for idle connections expire and packets get dropped into a black hole, so the client waits forever on a connection the kernel on the other side no longer knows about. Locally everything is loopback, so you never see it.

**Thread pool / executor starvation.** Sync-over-async, or a task blocking a pool thread while waiting on work queued to the same pool. CI runners typically have far fewer cores than your laptop, and most runtimes size default pools off core count — so a pool that's 16 wide locally is 2 wide in CI, and a starvation pattern that needs 3 concurrent blocked tasks suddenly becomes reachable. This explains "never locally" better than almost anything else.

**Subprocess pipe deadlock.** If your integration tests spawn a service, a DB client, or a docker command and don't drain its stdout/stderr, the child blocks forever once the 64KB pipe buffer fills. CI usually runs at higher log verbosity than local — which is exactly the variable that decides whether the buffer fills. Very CI-specific, very easy to miss.

**Lock-ordering deadlock, in-process or in the database.** Databases have deadlock detectors and will break these, *unless* it's a lock-wait (not a cycle) with a huge or disabled `lock_timeout`. In-process mutex deadlocks have no detector at all. Different CPU counts change interleavings enough to flip a 1-in-a-million race into 1-in-20.

**Cross-run contention.** If CI shares a Postgres/Redis/broker instance across concurrent jobs, an advisory lock or leftover row lock from another run blocks yours. The 5% then correlates with *how many jobs were running concurrently*, not with your code at all. Check whether hangs cluster by time of day.

**Not hung, just stalled.** Burstable instances exhausting CPU credits, or a runner with a memory limit thrashing. Distinguishable in seconds if you capture CPU state.

**Teardown misattributed as a test.** Many runners report the last-started test as "current," so a hang in fixture cleanup, a non-daemon thread, or an event loop with a pending handle looks like a hang *in* a test. Worth confirming you're actually stuck inside the body.

## On the pool theory specifically

Your skepticism is reasonable, but the hypothesis has one virtue: it makes a sharp, cheap prediction. Pool exhaustion is a *cumulative* mechanism, so it should hang at a stable position in the run, not a uniform one. And most pools have a checkout timeout — if yours does and it's set, exhaustion produces a loud exception, not a hang. It can only hang if the timeout is unset or infinite.

So the one-line experiment: **set the pool checkout timeout to 5 seconds.** Next hang either becomes a fast, well-labeled "could not acquire connection" with a stack trace pointing at the leak, or the run hangs exactly as before and the theory is dead. Either outcome is progress, and it costs one config line. Do the same for socket read timeouts on every client while you're in there — converting hangs into timeouts is generally the highest-leverage change you can make to a hanging suite.

## The instrumentation that discriminates all of these at once

You can't debug a hang by watching it. Add a watchdog to the CI job: if no test output for N minutes, before killing anything, dump —

- all thread/task stacks (`jstack`, `py-spy dump`, SIGQUIT, delve, `node --inspect` + CDP — whatever your runtime offers)
- `ss -tanp` for socket states (`ESTABLISHED` with a large `Recv-Q`, or `CLOSE_WAIT` piles, are damning), plus `lsof` fd counts
- `pg_stat_activity` and `pg_locks` (or your DB's equivalent) from a *separate* connection
- `ps`, `/proc/<pid>/status`, load average

That single artifact separates "blocked in socket read" from "blocked on mutex" from "waiting on pool" from "spinning" from "not actually running" immediately. Also add per-test timeouts well below the job timeout so you fail fast and get the dump.

Cheap supporting signal: log open connections, thread count, and fd count after every test. Monotonic growth = leak; flat = not a leak.

## Reproducing locally

Make local look like CI along the axes that matter, one at a time: `docker run --cpus=1` or `taskset -c 0` to force the low-core-count interleavings; CI's log level, not yours; `tc netem` to add latency and drop packets; and run four copies of the suite concurrently against one shared database. Then loop the suite 100 times. If constraining CPU alone reproduces it, you're looking at pool starvation or a race; if shared-DB concurrency reproduces it, it's cross-run contention.

**Order I'd attack this in:** (1) pull hang positions out of existing logs to classify the pattern, (2) add the watchdog dump, (3) set pool and socket timeouts to convert hangs into labeled errors. Steps 1 and 3 are close to free, and between them they'll probably settle the pool argument before you've spent real effort.