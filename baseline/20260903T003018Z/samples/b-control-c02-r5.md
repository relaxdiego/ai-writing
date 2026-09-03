Your skepticism is well-founded, and the signature itself is doing a lot of work here. Let me unpack what it implies before listing suspects.

## What the three clues actually tell you

**"Always a different test"** means the hanging test is almost certainly not the guilty test. It's the one that happened to be holding the bag. This points at either (a) something that accumulates across the run until a threshold is crossed, or (b) a race window that any test can lose. It also raises an easy question: is your test order randomized in CI? If so, "different test each time" may just be "different order each time," and the real culprit is whatever ran *immediately before* the hang.

**"Never locally"** is the strongest clue and it's usually one of four differences: fewer/throttled CPUs (widens timing races, shrinks thread pools), output captured through a pipe instead of a TTY, shared infrastructure with concurrent CI jobs, and container networking (DNS, NAT idle timeouts, no keepalives).

**"1 in 20"** is a frequency that argues *against* a pure accumulation model. A leak that crosses a threshold tends to be much more deterministic once you're over it — you'd see it 1 in 2, not 1 in 20. A 5% rate smells like a race, or like a rare trigger (occasional slow query, occasional timeout) that *then* causes a leak.

## Why pool exhaustion is a weak fit as stated

Every mainstream pool has a checkout timeout by default — HikariCP 30s, SQLAlchemy `pool_timeout` 30s, etc. Exhaustion normally produces a loud error with a stack trace, not an indefinite hang. For it to hang forever, someone would have had to disable that timeout.

The steelman version is more interesting and does fit: an occasional slow operation trips a test-level timeout, the cleanup path is skipped, and a connection is orphaned **with an open transaction**. Now it's not pool exhaustion that hangs you — it's the *next* test blocking forever on a row/table lock held by a connection that's `idle in transaction`, with no `lock_timeout` set. That composite explains the randomness, the accumulation, and the CI-only aspect (shared DB, concurrent jobs). Worth testing specifically, and it's cheap to test.

## The other realistic candidates

- **Lock waits on a shared database** — the composite above, or two concurrent CI jobs against the same DB instance racing on migrations/advisory locks.
- **Thread-pool or event-loop deadlock** — a blocking call on the async loop, or a task waiting on another task queued behind it in the same bounded pool. Classic CI-only, because CI gives you 2 cores and your laptop gives you 10, so the pool is smaller and the deadlock becomes reachable.
- **Subprocess pipe deadlock** — a child process fills the 64KB stdout pipe, nobody drains it, child blocks on `write()`, parent waits on `wait()`. Almost perfectly CI-specific: locally you have a TTY, in CI output goes through a pipe. Badly underrated.
- **Blocked on stdin with no TTY** — git asking for a credential, gpg/pinentry, sudo. Waits forever.
- **Socket read with no timeout** — most default socket timeouts are infinite. Cloud NAT gateways silently drop idle connections (often ~350s); without TCP keepalives your side sits in ESTABLISHED forever talking to nobody.
- **Lost wakeup** — a "wait for service ready" condition variable where, under CPU contention, the notify fires before the wait registers.
- **Memory pressure** — cgroup limits causing GC thrash or an OOM-kill of a helper, leaving the test waiting on a corpse.

## How to tell them apart

**The single highest-value move: make the hang produce an artifact.** Right now you get a job timeout and no information, which is why you're reasoning from priors. Add a watchdog that fires ~2 minutes *before* the CI job timeout and dumps:

- All thread/task stacks — `jstack` or `kill -QUIT` (JVM), `py-spy dump --pid`, `SIGQUIT` (Go), `SIGUSR1`/inspector or `process._getActiveHandles()` (Node), `dotnet-stack` (.NET), `rbspy` (Ruby).
- `pg_stat_activity` — `state`, `wait_event_type`, `wait_event`, `xact_start`, `query`, plus `pg_blocking_pids(pid)`. Or `SHOW ENGINE INNODB STATUS` for MySQL.
- `ss -tanpo` and `lsof -p`, plus pool gauges (active/idle/waiting).

One good dump usually ends the debate outright. `timeout -s QUIT` around the runner is often enough to wire this up.

**Second highest-value: set finite timeouts everywhere** — pool checkout, socket connect and read, `statement_timeout`, `lock_timeout`, `idle_in_transaction_session_timeout`. This is a structural fix, but it's also a *discriminator*: whichever timeout fires tells you the layer, and you've converted an unfalsifiable hang into an ordinary stack trace.

Then the cheap experiments:

| Hypothesis | Discriminating test | Expected signal if true |
|---|---|---|
| Accumulation/leak | Log the ordinal position of the hanging test across ~20 hangs | Back-loaded distribution; uniform ⇒ race, not leak |
| Pool exhaustion | Emit pool active/idle/waiting after each test | Ratcheting sawtooth that never returns to baseline |
| Orphaned transaction / lock wait | `idle in transaction` sessions + `pg_blocking_pids` at hang time | A blocker whose `xact_start` predates the hanging test |
| Cross-job contention | Unique DB/namespace per CI job | Hang disappears |
| Intra-suite parallelism | Run with parallelism=1 in CI | Disappears ⇒ worker contention; persists ⇒ environmental |
| Ordering | Record and replay the RNG seed; log the preceding test | A consistent predecessor across hangs |
| Thread-pool deadlock | `docker run --cpus=2 --memory=2g` locally, loop 200× | Reproduces locally under constraint |
| Pipe deadlock | Pipe suite output to a file locally, not a TTY; check child `/proc/PID/stack` | Child blocked in `write()` to pipe |
| Dead socket | `ss -tanpo` during hang | ESTABLISHED with no timer, peer unresponsive |

**Practically:** don't debug one hang at a time at a 5% rate. Add the watchdog and the dumps, then run the suite 100× in a matrix job overnight. You'll collect ~5 hangs with full diagnostics and the answer will likely be obvious — that beats another round of hypothesizing.

If you tell me the language/runtime and whether CI jobs share a database instance, I can narrow this down considerably.