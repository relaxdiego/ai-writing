Your skepticism is well-placed, but not because pool exhaustion is implausible — it's that "hangs at a different test each time" is the single most informative fact you have, and it's compatible with about eight causes, of which the pool is one.

## What the evidence actually constrains

A varying hang site rules out "one bad test" and points at something shared: a global resource, a background thread, the harness itself, or the environment. It does *not* rule out a consistent culprit — a test that leaks a connection, an open transaction, or a lock and lets the *next* arbitrary test block on it looks exactly like a random victim. Distinguishing "random cause" from "consistent poisoner, random victim" is a separate question you'll answer from the artifacts below.

One caveat that trips people up: the test you think it hangs on is usually just the last test whose output flushed. Under buffered/piped output in CI, that can be several tests behind the real one, or the run may actually be hung *after* the last test, on teardown. Confirm which before theorizing further.

## The plausible set

**Shared-resource waits.** Pool exhaustion, yes — but also a lock wait (an idle-in-transaction session holding a row or a DDL lock while another worker blocks indefinitely; databases abort true deadlocks, but a one-way wait can last forever), or an advisory/migration lock taken by a worker that died.

**Concurrency you only have in CI.** If CI runs N workers and you run one locally, that difference alone explains "never locally." Two workers sharing a database, a fixture directory, or a port collide at some rate.

**Missed-wakeup races.** A future/promise that never resolves because an event fired before the listener attached. These are pure scheduling luck, so a slower or differently-loaded machine flips them. Frequently the shared helper is used by many tests, hence the varying site.

**Output pipe backpressure.** CI captures stdout through a pipe; locally you have a TTY. If a child process fills a pipe nobody drains, it blocks on `write()` at an essentially arbitrary point. This matches your symptoms disturbingly well and is almost never the first guess.

**A dead peer with no timeout.** If a service container gets OOM-killed, existing TCP connections often black-hole rather than reset, and a client with no socket timeout waits forever. Check for exit code 137 and kernel OOM messages.

**Runtime thread-pool starvation.** Node's libuv pool (default 4) saturated by fs/DNS work, a fixed-size executor, a starved async runtime — all present as a hang with an idle main thread.

**Leaked handles at teardown.** A lingering child process, timer, or server socket keeping the runner alive after the last test passes.

## The artifact that collapses most of this

Don't reason further from the outside. Make the hung process tell you where it is. Add a watchdog to the CI job that fires a few minutes before the job timeout and captures:

- A stack/thread dump of every test process. `SIGQUIT` for a JVM thread dump; `SIGABRT` or `runtime.Stack` for Go; `py-spy dump --pid` or a pre-registered `faulthandler` for Python; `node --report-on-signal` plus `SIGUSR2`, or `why-is-node-running`, for Node.
- `ps auxf`, `ss -tanp`, and the container logs for every service.
- `pg_stat_activity` and `pg_locks` (or `SHOW ENGINE INNODB STATUS`), which distinguishes pool exhaustion from lock waiting in one glance.
- `dmesg | tail` for OOM kills.

One good dump usually ends the investigation. Everything below is for the case where you want to move before you catch one.

## Cheap experiments, and what each predicts

**Set a pool acquire timeout.** If the theory is right, the hang becomes a clean "timed out waiting for connection" error at the next run, with a stack trace naming the test. This is the fastest way to confirm or kill the pool hypothesis, and you want the timeout in place permanently regardless. Corollary: doubling the pool size should roughly halve the rate, and halving it should make the hang frequent. A cause that doesn't respond to pool size isn't the pool.

**Drop to one worker.** If the hang disappears, it's cross-worker contention — a lock, a shared fixture, or a port. If it survives, look at the async races and the runtime thread pool.

**Fix the random seed** (if your runner randomizes order). A reproducible seed turns a 5% flake into a deterministic one, at which point bisection is mechanical.

**Constrain CPU locally.** `docker run --cpus=1 -m 2g`, output redirected to a pipe rather than a TTY, no TTY allocated, suite in a loop for a few hundred iterations. This reproduces the three things CI has that your laptop doesn't. If it reproduces, you're done guessing. It also amplifies missed-wakeup races specifically — those get *more* frequent as you starve the scheduler, which most other causes don't.

**Add timeouts to every HTTP and socket client.** Same logic as the pool timeout: it converts silent hangs into located failures. A suite that can hang indefinitely anywhere is telling you there's an unbounded wait somewhere in your stack, and that's worth fixing on its own terms.

If you tell me the language, test runner, and whether CI parallelizes, I can narrow this to the two or three that actually fit and give you the exact dump incantation.