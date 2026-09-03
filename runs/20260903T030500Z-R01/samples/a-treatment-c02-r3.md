Your skepticism is well-founded, and it's worth naming why. A leaked-connection pool exhaustion is *cumulative*: every run leaks at the same rate, so the pool should run dry at roughly the same point in the suite every time, and the failure should be near-deterministic rather than 1-in-20. A 5% rate that lands at a random test looks much more like a timing race or contention on something shared outside the process.

## First: stop guessing, capture a stack

This single move collapses most of the hypothesis space, so do it before any of the reasoning below:

- **Python**: `faulthandler.dump_traceback_later(600, exit=True)` in a session fixture, or `pytest-timeout` with `--timeout-method=thread`, which dumps every thread's stack on fire. Better still, have CI run `py-spy dump --pid <pytest pid>` from a watchdog step when the job nears its limit.
- **JVM**: `jstack`, or just `kill -QUIT` — thread dump to stdout, with lock ownership.
- **Go**: `SIGQUIT` gives you all goroutines. Go's `-timeout` does this for you already.
- **Node**: `kill -SIGUSR1` and attach, or `why-is-node-running`.

The key detail is that CI jobs usually get killed by the *outer* timeout, which tells you nothing. You want a timeout strictly inside that budget which dumps state before dying. One good stack trace ends this investigation.

## Cheap signals in the data you already have

- **Ordinal position vs. test identity.** If your runner randomizes order, check whether hangs cluster at a similar *test number* even though the test *name* differs. Same depth → cumulative resource exhaustion (the pool theory earns its keep). Random depth → race or external contention.
- **Concurrency correlation.** Do hung runs coincide with other CI jobs running at the same time? Shared Postgres/Redis/Kafka, a shared schema, or an advisory lock two jobs both want will produce exactly this: rare, order-independent, and structurally impossible to reproduce on a laptop running one suite alone.
- **Runner shape.** CI boxes typically have fewer cores and a hard cgroup CPU quota. Under quota-induced throttling, a thread can be descheduled for hundreds of milliseconds, which opens interleavings that essentially never occur on an 8-core laptop. This is the single biggest reason "never hangs locally" is uninformative.

## The candidates worth ranking

**Lost wakeup / deadlock in async or threaded code.** A condition set before the waiter starts waiting, two locks taken in opposite orders, an `asyncio` task awaiting a future nothing will ever complete. Predicts: random position, no CPU burn while hung, stacks parked in `wait`/`select`/`futex`. Most likely fit for your symptoms.

**A socket read with no timeout.** A dependency container drops a connection, or a TCP connection blackholes and retransmits forever. HTTP clients and DB drivers default to *no* read timeout in more libraries than people expect. Predicts: stack sitting in `recv`, and `ss -tnp` showing an established socket with a stuck send queue.

**Pipe buffer deadlock.** A test spawns a subprocess, the parent waits on exit without draining stdout, and the child blocks writing once the 64 KB pipe fills. This is *inherently* CI-only: locally you run against a terminal, in CI everything goes through a pipe. Predicts: parent in `waitpid`, child in `write`. Rare because it depends on how chatty that particular child happened to be.

**Test-framework parallelism.** With `pytest-xdist` or similar, a worker that segfaults or OOMs leaves the controller waiting on a channel that will never speak again. Predicts: the "hanging test" is just whatever was dispatched last; look for a missing worker process and a dmesg OOM kill.

**Pool exhaustion, properly.** Don't discard it — instrument it. Log pool checkout counts periodically (SQLAlchemy's `pool.status()`, HikariCP's metrics). If a hang shows a full pool with all connections checked out and idle, you have your answer, and the real bug is a code path that leaks on an exception. Set `pool_timeout` regardless: a pool that raises after 30 seconds converts a hang into a stack trace naming the culprit.

The ordering I'd work in: add an in-suite timeout that dumps all thread stacks, set explicit socket and pool timeouts everywhere (each one turns a hang into a labeled failure), then re-run until it trips. At 5%, twenty CI runs of an empty-change PR gets you a reproduction with roughly 64% probability; forty gets you 87%. That's cheaper than reasoning about it further.