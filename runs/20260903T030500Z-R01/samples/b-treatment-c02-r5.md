Your skepticism is reasonable, but not for the reason you might think — pool exhaustion is actually *compatible* with "always a different test," since a leak accumulates and whoever crosses the threshold is the victim. What makes it doubtful is that a leak has a signature you can check in ten minutes, and it usually isn't there.

## What the symptom pattern actually tells you

**"Different test each time"** means the hanging test is almost certainly not the cause. Either state accumulated from earlier tests, or a race whose timing is set by something outside the test.

**"Never locally"** points at what CI has that your laptop doesn't: fewer cores (so a thread-pool or event-loop starvation bug that never manifests at 10 cores appears at 2), higher and more variable network latency to service containers, non-tty stdout, different parallelism, and neighbours competing for the same host.

**"1 in 20"** is a race, not a resource ceiling. True exhaustion tends to be far more reproducible once the leak rate exceeds the pool size.

## Plausible mechanisms

*Accumulating resource leaks* — connections, but also file descriptors, threads, or subprocesses. Distinguishing marker: the hang position drifts *later* in the run, and is roughly stable under a fixed test order.

*Cross-worker contention* — parallel workers sharing a database, fixture rows, ports, or temp paths. Two workers deadlock on locks, or one blocks on a row the other holds in an unfinished transaction. If your DB has no `lock_timeout`, that's an infinite wait. Local runs often use lower parallelism, which hides it.

*Missing timeouts on external calls* — a request to a service container that never answers. Locally the dependency is fast and healthy; in CI it hiccups once every few hundred calls. A hang is, definitionally, the absence of a timeout somewhere.

*Runtime starvation* — a blocking call on an async runtime, or sync-over-async. With 2 CPUs and a small worker pool, the pool gets fully occupied and nothing can complete.

*Lost wakeup* — a condition variable signalled before the waiter waits, or a queue consumer that exits without draining. Pure timing; CPU contention flips it.

*The stdout pipe deadlock* — an underrated CI-only classic. A subprocess writes to a pipe nobody drains, the 64KB buffer fills, the write blocks forever. Locally you have a tty and different buffering. This one naturally hits at a different test each run, because it depends on cumulative output volume.

## How to tell them apart, cheapest first

**Get a stack dump of the hung process.** This is worth more than every other step combined, and it's the step most teams skip because CI kills the job with no artifact. Set your job timeout *below* the CI hard timeout and have it send SIGQUIT (JVM, Go) or run `py-spy dump --pid`, `jstack`, `node --report`, or `gdb -p ... -ex 'thread apply all bt'` before dying. One dump usually ends the investigation: you'll see every thread parked in `pool.acquire`, or two threads in a lock cycle, or one thread in `write()` on fd 1.

**Set finite timeouts everywhere** — pool acquisition, HTTP client, socket read, DB statement and lock timeout. This doesn't fix anything, but it converts a silent hang into a stack trace with a message. Run it that way for a week and read what it says.

**Emit pool and fd counts at every test teardown.** Monotonic growth confirms the leak theory outright; flat counts kill it. `lsof -p`/`/proc/pid/fd` count is the same check for descriptors.

**Run the suite serially in CI.** If ten serial runs never hang, it's cross-worker contention, and you can look at shared fixtures, shared DB state, and port allocation. If it still hangs, parallelism is irrelevant.

**Log each test's ordinal position and duration.** Plot where the hangs land across ~20 occurrences. Clustering late = accumulation. Uniform scatter = race. Also check whether the hanging tests share a subsystem even though their names differ; that's the shared-resource tell.

**Reproduce under CI-like constraints locally.** Same container image, `--cpus=1 --memory=2g`, same parallelism, stdout redirected to a file rather than a tty, suite in a loop 50 times. If this reproduces it, your iteration cycle drops from an hour to a minute — and if it *doesn't* reproduce after the CPU and tty changes, that itself narrows things toward the network path to your service containers.

**Correlate against infrastructure.** Runner ID, image version, time of day. A single sick host or a noisy-neighbour window explains a surprising number of 5% flakes and costs nothing to check from data you already have.

If I had to bet before seeing a stack dump: missing timeout on a call to a service container, or lock contention between parallel workers. But the dump is what settles it, and everything else is guessing.