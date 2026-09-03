Your skepticism is reasonable, but the more useful move is to notice that the pool hypothesis is cheap to kill outright — and that the symptoms you have already narrow the field a lot.

## What the symptoms are telling you

**It hangs rather than fails.** That means some wait in the system has no upper bound. This is independently a defect, separate from whatever triggers it. Nearly every layer has a timeout that defaults to infinite when you don't set it: Postgres `lock_timeout` (0 = forever), `node-postgres` `connectionTimeoutMillis` (0 = forever), a bare `socket.recv()`, a `Future.get()` with no deadline. Whatever the root cause turns out to be, you have a missing bound too.

**Always a different test.** This is evidence for shared state or environment and against a single buggy test — *but only if your test order is deterministic*. If your runner randomizes order or shards across workers, "different test each time" is exactly what one consistently-guilty test looks like. Check this before you weight it.

**Never locally.** The interesting question is which axis differs. The usual suspects: core count (pool and executor sizes derived from CPUs — 10 cores locally, 2 in CI), parallelism (workers vs. serial), `fork` vs `spawn` (Linux CI vs. macOS dev), shared infrastructure (CI runs share a database/Redis/namespace; you don't), network path (localhost vs. a container network with NAT and conntrack), and run duration (a full suite crosses idle-timeout thresholds a single local file never reaches).

## Mechanisms that fit "1-in-20, random test, CI only"

**Connection leak, not exhaustion per se.** A conditional path (early return, exception, un-rolled-back transaction) fails to return a connection. Fits the symptoms *if* the leak is itself conditional. Watch for the tell: exhaustion should poison everything after the first victim, and the hang should land at a consistent depth into the run, roughly correlated with pool size.

**Stale pooled sockets.** This is where your colleague is probably half-right. The pool isn't scarce, it's holding dead connections. Something between client and server silently reaps idle connections — NAT/conntrack expiry, a load balancer idle timeout, `idle_in_transaction_session_timeout`, a container restart. The client gets no RST, so the next use blocks in `recv()` until TCP keepalive fires, which is ~2 hours by default, or never. Long CI runs sit idle in ways local runs don't.

**Lock waits behind an abandoned transaction.** Leaked connection with an open write transaction; a later test's setup does `TRUNCATE` (needs `ACCESS EXCLUSIVE`) and blocks forever, because Postgres `lock_timeout` defaults to infinite and the deadlock detector never fires — this is a wait, not a cycle. Which test dies depends purely on ordering.

**Thread-pool or event-loop starvation.** A task submitted to a bounded executor blocks waiting on another task in the same executor. Local pool size 10, CI pool size 2 → only CI deadlocks.

**Fork with inherited locks.** Forking a process that holds a malloc/logging/HTTP-client lock; the child deadlocks in a lock no one will release. Python's `multiprocessing` defaults to `fork` on Linux and `spawn` on macOS, which alone explains "never on my machine."

**Cross-run interference.** Two concurrent CI runs sharing a database, advisory lock, or migration lock. 1-in-20 ≈ how often two runs overlap.

**A blocked stdout pipe.** A subprocess fills the 64KB pipe buffer, nobody drains it, child blocks in `write()`, parent blocks in `wait()`. Locally your terminal drains it or the output is smaller.

## The artifact that settles it

Stop reasoning and get a stack dump from the hung process. Right now your CI timeout `SIGKILL`s the job and you learn nothing. Set the job timeout *above* a watchdog that dumps state first:

- **Go**: `go test -timeout 60s` already panics with every goroutine stack. Free.
- **Python**: `faulthandler_timeout` in pytest ini, or `pytest-timeout` with `--timeout-method=thread`; `py-spy dump --pid` for a live process.
- **JVM**: `SIGQUIT` → thread dump, or `jstack`.
- **Node**: `--detectOpenHandles`, `process._getActiveHandles()`, `SIGUSR1` for the inspector.

Dump the **server** side too, not just the test process. And snapshot the environment at the same moment: `ss -tanp`, pool active/idle/waiting counts, and `pg_stat_activity` (state, `wait_event_type`, `xact_start`) joined against `pg_blocking_pids()`.

That one artifact discriminates almost everything:

| Where the stack sits | Diagnosis |
|---|---|
| `pool.acquire` / `getConnection` | Genuine exhaustion |
| Socket `recv`, no server-side counterpart | Stale connection |
| DB driver + `pg_locks` shows an `idle in transaction` blocker | Abandoned transaction |
| `executor.submit` / `future.get`, all workers busy | Pool starvation |
| Child in `write()`, parent in `waitpid` | Blocked pipe |
| A lock acquired before `fork` | Fork safety |
| Advisory lock held by another run's session | Cross-run collision |

## Killing the pool hypothesis in ten minutes

Set the acquire timeout to 5 seconds and make it throw. If it's exhaustion, the hang converts into a clean "timeout acquiring connection" with a stack pointing at the victim — and you can then log the holders. If the hang is unchanged, the pool isn't it.

Then move the pool size. Set max to 1: exhaustion should go to near-100% frequency. Set it to 3×: frequency should collapse. **A hypothesis that doesn't move when you move the pool size isn't about the pool.**

Alongside that, enable leak detection (HikariCP's `leakDetectionThreshold`, or wrap checkout/release in a registry that logs the stack of any connection held longer than N seconds).

## Do this regardless

Put finite bounds on every wait: per-test, per-HTTP-request, per-DB-statement (`statement_timeout`), per-pool-acquire, per-lock-wait (`lock_timeout`). This converts hangs into failures with stack traces and makes every subsequent investigation cheap — including the ones for the bugs you haven't hit yet.

And instrument the run so a hang leaves a trail: record the ordering seed, log which test each worker was running (not just the last line of output), and log completed-test count and elapsed time. Then check whether the hang position correlates with test count (a leak exhausting a fixed budget — connections, file descriptors, ports) or with wall time (an expiry — token TTL, idle reaper, lease). That correlation alone splits the field in half.

If you tell me the language and test runner, I can give you the exact watchdog and dump invocation.