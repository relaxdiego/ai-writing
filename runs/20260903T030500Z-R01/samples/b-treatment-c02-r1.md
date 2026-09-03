Your skepticism is reasonable, but not because pool exhaustion is implausible — it's because the hypothesis hasn't been made to predict anything yet. Pool exhaustion makes a sharp, checkable prediction: a leak is cumulative, so hangs should cluster in the **late** portion of the run, and pool checkout counts should climb monotonically across tests. If the hangs are uniformly distributed across the run, or the pool high-water mark is flat, the theory is dead in ten minutes. That question is worth more than the argument.

Meanwhile, here's what else fits all three facts (CI-only, ~5%, different test each time).

## Candidate families

**Blocking network call with no timeout.** This is the enabler behind most CI-only hangs. In CI your dependencies are containers behind a NAT layer, and that layer does things loopback never does: conntrack drops idle flows, a service restarts and the peer never sends a FIN, DNS resolution stalls. If your DB/HTTP client has no read timeout and no TCP keepalive, that socket read blocks forever. Explains all three facts cleanly — any test can be the victim, the rate is low, and locally there's no NAT to drop anything.

**Database lock, not connection, exhaustion.** A prior test leaves a transaction idle-in-transaction holding a row lock; the next test touching that row waits on a `lock_timeout` that defaults to infinity. Superficially resembles pool exhaustion, entirely different fix.

**Harness concurrency.** CI almost certainly runs a different worker count than you do (`nproc` on the runner vs. your laptop), and CI machines are CPU-oversubscribed, which widens race windows by orders of magnitude. Two workers colliding on a shared fixture, a fixed port, a temp directory, or a lost notify/unawaited task all produce exactly "random test, sometimes."

**Subprocess pipe deadlock.** If any test shells out and the parent waits for exit before draining stdout/stderr, the child blocks once it fills the ~64KB pipe buffer. This is a notorious CI-only hang, because locally you have a TTY and often different log verbosity.

**It isn't hanging where you think.** With buffered output, the last test name you see is not the test that hung — it's the last one that flushed. Worth confirming there's a *completion* line for the previous test before you trust the location at all. Related: the suite may have actually finished and the process won't exit (non-daemon thread, unclosed executor, lingering container client).

## Make the next hang pay for itself

Stop reasoning from the outside. Add a CI watchdog that fires below the job timeout and, *before* killing anything, dumps:

- Thread/goroutine/task stacks of the test process — `SIGQUIT` (JVM/Go), `faulthandler` or `py-spy dump --pid` (Python), `SIGUSR1` + inspector (Node).
- `ss -tanp` and `lsof -p` for the process.
- `SELECT * FROM pg_stat_activity` / `SHOW FULL PROCESSLIST`, plus `pg_locks` or `SHOW ENGINE INNODB STATUS`.

One artifact discriminates nearly everything above. A stack sitting in `pool.acquire` says pool. Sitting in `recv` on a live socket says missing timeout. Sitting in `waitpid` says pipe deadlock. A `futex`/monitor wait says harness concurrency. And `idle in transaction` in `pg_stat_activity` says lock, not pool.

## Cheap falsifying experiments, in order

1. **Log pool checkout count and high-water at every test teardown.** Directly settles your colleague's theory, one run.
2. **Set aggressive timeouts everywhere** — socket connect/read, `statement_timeout`, `lock_timeout`, per-test deadline. This converts every hang into a failure with a stack trace, which you want permanently regardless of the cause.
3. **Drop CI parallelism to 1** on a branch and loop the suite 50×. If the hang vanishes, it's concurrency or a shared fixture, not a leak. If it survives, you've eliminated a whole family.
4. **Pin the test seed/order** and loop again. Stable victim ⇒ order-dependent state left behind by a specific predecessor; still-random victim ⇒ timing.
5. **Reproduce the environment, not the code.** Run the CI image locally under the same `--cpus` limit and worker count. "Never locally" usually means "never at 1/8th the contention" rather than anything about the machine.

Steps 1 and 2 are a couple of hours and are useful even if you learn nothing. Step 2 in particular is the one durable fix here: a suite where any operation can block forever will keep inventing new ways to hang, and the specific cause you find this week is less valuable than removing the possibility of an unbounded wait.