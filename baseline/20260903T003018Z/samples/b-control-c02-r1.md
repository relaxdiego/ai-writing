Your skepticism is well-placed — not because pool exhaustion is wrong, but because "different test every time" is a much stronger clue than it's being given credit for, and it points at a whole family of causes of which pool exhaustion is just one member.

## What the symptom pattern actually tells you

**The test that hangs is probably the victim, not the culprit.** When failures land on a different test each run, either the test order is changing, or the failure depends on accumulated state / cross-process timing rather than on the test's own code. So the first two questions are cheap and highly discriminating:

- **Is your test order randomized?** pytest-randomly, RSpec, `go test -shuffle`, and JUnit method ordering all randomize by default or by config. If so, "different test each time" may be a *fixed* culprit pair being reshuffled. Log the seed on every run, and check whether the hung test is consistently preceded by the same test.
- **Does the hang happen at a consistent *position* in the run rather than a consistent *name*?** If it always dies around test #180 regardless of which test that is, you have cumulative exhaustion — leaked connections, file descriptors, threads, ports. If the position is random too, you have a race or contention issue.

**A hang, not a failure, means something has no timeout.** This is worth separating from root cause. A transient network blip, a slow query, or a lost response should surface as an error in seconds. It surfaces as a hang because somewhere — an HTTP client, a DB driver, a socket read, a queue consumer, a lock acquisition — there's a wait with no deadline. Whatever the trigger turns out to be, the missing timeout is an independent bug and the reason you have no diagnostic information.

## The realistic candidate list

**Cross-worker database contention.** CI usually runs tests in parallel workers; locally you probably run serially or with fewer workers. Two workers touching the same rows, the same sequence, an advisory lock, or a migration table can block each other indefinitely. Postgres detects deadlock cycles, but a plain lock wait doesn't self-resolve — it waits forever unless `lock_timeout` is set.

**Thread pool sized from the wrong core count.** In a container with a CPU quota, older JVMs, Go runtimes, and many libraries read the host's core count (say 64) while the cgroup allows 2. Or the inverse: a pool sized to `nproc` where a task blocks waiting on another task in the same pool — classic pool-starvation deadlock that only triggers when the pool is small. Local machines are usually unconstrained, so the bug never opens.

**Connection pool exhaustion — the suggested cause.** Plausible mechanism: a test path leaks a connection (an unclosed transaction, an error path that skips release), and the Nth test to ask for a connection blocks forever because the pool has no acquire timeout. This *does* fit "different test, cumulative, never locally (fewer parallel workers, so the leak never adds up to the pool size)." It's worth taking seriously, and it's trivially falsifiable — see below.

**Test isolation leak.** A fake/frozen clock left installed by a previous test, so a `sleep`/retry/timeout in a later test never advances. An unawaited promise or a mock left on a global. A background consumer killed by a prior test's cleanup, so a later test waits on a queue nobody drains. This fits the pattern almost too well.

**Silent connection death.** Cloud NAT and conntrack tables drop idle flows after ~350s without sending a RST. If TCP keepalive is off and the read has no timeout, the client waits essentially forever on a socket the network has already forgotten. This happens in CI and not on loopback locally.

**Service-readiness race.** A dependency container passes a TCP-accept health check but isn't application-ready, so the first real request goes into a black hole. 1-in-20 is a very typical rate for a startup race.

Less likely but cheap to rule out: file-descriptor or ephemeral-port exhaustion, DNS resolution hanging in the container, a full stdout pipe blocking the process, or a GC death spiral (which looks like a hang but pins the CPU).

## How to tell them apart

Stop reasoning about it and make the hang produce evidence. At 1-in-20, you need roughly 20 runs to catch one — that's an afternoon, not a research project.

Add a watchdog to the CI job: a timeout *shorter* than the job limit that, before killing anything, dumps state. The single highest-value artifact is a **full stack dump of every thread/goroutine/task**:

- JVM: `jstack <pid>` or `kill -3`
- Go: `SIGQUIT` (dumps all goroutines with their wait reasons)
- Python: `py-spy dump --pid <pid>`, or `faulthandler.dump_traceback_later`
- Node: `why-is-node-running`, or `process.report.writeReport()`

Alongside it, capture:

- `ss -tanp` — socket states and queue depths, per process
- `SELECT pid, state, wait_event_type, wait_event, query, xact_start FROM pg_stat_activity` plus `pg_locks` for blockers
- `lsof -p <pid> | wc -l` against `ulimit -n`
- CPU usage of the hung process

That set separates every hypothesis above in one shot:

| What you see at hang time | Diagnosis |
|---|---|
| Threads parked in `pool.acquire` / `getConnection`, DB shows few active sessions | Pool exhaustion — and the leak is on the client side |
| Many sessions `idle in transaction` with old `xact_start` | Leaked transactions (the *cause* of the above) |
| `wait_event_type = Lock`, one session blocking others | Cross-worker lock contention |
| Socket `ESTABLISHED` with nonzero `Recv-Q`/`Send-Q` and no DB activity | Dead connection / missing timeout / NAT drop |
| Threads blocked on a queue or future, pool at max, nothing running | Thread-pool starvation deadlock |
| Stack sitting in `sleep`/timer wait that should have fired | Fake clock or test isolation leak |
| CPU pinned at 100% | Not a hang — GC spiral or livelock |
| fd count at the ulimit | Descriptor leak |

Two supporting moves worth doing in parallel: set **timeouts everywhere** (pool acquire, socket read/connect, statement, `lock_timeout`) — not as a fix, but so the next occurrence produces a stack trace at the point of failure instead of silence. And **try to reproduce locally by making local look like CI**: run the suite in a loop under `docker run --cpus=2 --memory=2g`, with CI's worker count, against a shared DB, ideally with a little injected latency (`tc qdisc add dev eth0 root netem delay 50ms`). If it reproduces, your iteration loop goes from twenty CI runs to two minutes.

## Where I'd put my money

If forced to guess before seeing data: a missing timeout is definitely present (that's what makes it a hang rather than a flake), and the trigger is most likely cross-worker contention or a leaked resource that only accumulates at CI's parallelism. Pool exhaustion is a reasonable specific hypothesis inside that space — the right response to it isn't to argue, it's to add the instrumentation that would confirm or kill it in a single hung run. Your colleague's theory and four others all get resolved by the same stack dump.