Your skepticism is well-placed, but not for the reason you might think — the pool theory is *plausible*, it's just under-specified. Let me lay out what the evidence actually constrains, then how to cut the space down.

## What "a different test each time" really tells you

It rules out a single buggy test and points at something global: shared state that accumulates across tests, a background thread, an external dependency, or the harness itself.

One caveat first, because it invalidates a lot of reasoning: **"hangs at test X" is usually inferred from the last line of output**, and with block-buffered stdout (which is what you get when CI captures output through a pipe rather than a TTY) the last line printed can be tens of seconds behind where the process actually is. If your runner buffers, "a different test each time" may be an artifact, and the real hang could be at a fixed point — often *after* the last test, with a non-daemon thread or leaked child process keeping the process alive. Confirm you're running unbuffered (`PYTHONUNBUFFERED=1`, `stdbuf -o0`, `-race`-style unbuffered writers, etc.) before you trust the "random position" observation at all.

## The pool hypothesis, resolved in two minutes

A connection pool that runs out of connections only *hangs* if its acquire path has no timeout. So check your pool's config:

- **Go `database/sql`** and **node-postgres**: block indefinitely by default. Pool exhaustion here really does look like a hang. Hypothesis stays live.
- **HikariCP** (30s default) and **SQLAlchemy** (`pool_timeout=30`): raise an exception on exhaustion. If you're on these with defaults and you get a *hang* rather than a `TimeoutException`/`TimeoutError`, the pool is largely exonerated.

Either way, set an explicit short acquire timeout. That converts the failure mode from "silent hang" into "loud stack trace at the leak site," which is a strict improvement regardless of whether the pool is the cause.

Second cheap check: pool exhaustion from a leak is *cumulative*, so hangs should be biased toward the back of the run. You likely have 10–20 historical hangs in CI logs already. Pull the test index at hang time for each. Uniform across the run → not a leak. Clustered in the last third → leak of something (connections, fds, threads, ports).

## Other live candidates, with distinguishing signatures

**Thread-pool self-deadlock from low core count.** A task submitted to a bounded executor from *within* a task on that executor deadlocks only when the pool is too small to absorb it. Your laptop has 8–16 cores; the CI runner has 2. This is one of the best explanations for "never locally" and is invisible until you constrain cores. Signature: threads parked in `get()`/`await` on a future whose work is queued behind them.

**Concurrent CI jobs sharing one database.** If runs share a Postgres/Redis instance, a `SELECT FOR UPDATE`, advisory lock, or DDL lock held by *another run* blocks yours forever. Explains 1-in-20 (only when runs overlap), explains never-locally (you're alone), explains random position. Test: correlate hang timestamps against overlapping job start times. Very often the answer.

**Missing socket read timeouts.** CI networking differs — NAT, egress proxies, IPv6-vs-IPv4 resolution order, container DNS. A socket with no read deadline against a peer that silently drops the connection hangs forever. Signature: thread in `socketRead`/`epoll_wait`, `ss -tanp` shows an ESTABLISHED or SYN_SENT socket with a non-empty send queue.

**A dependency container died mid-run.** OOM-killed database or mock server; your test process survives and waits on a corpse. Signature: dependency container exit code 137, and your process blocked on I/O to a port nothing is listening on.

**Lost wakeup.** `wait()`/`notify` where the notify fires before the wait, or a condition variable without a predicate loop. Textbook 1-in-20 timing race that different CPU counts expose. Signature: exactly one thread parked with no counterparty.

**Memory pressure short of an OOM kill.** cgroup limit reached, heavy GC thrash or swap — looks like a hang, isn't one. Signature: `memory.current` pinned at `memory.max`, high CPU in GC.

## The move that actually ends this

Stop letting CI's job timeout kill the process. You're destroying the only evidence that matters. Add a suite-level timeout *shorter* than the job timeout, and on fire, dump state and upload it as an artifact:

- **All thread stacks** — `jstack`, `kill -QUIT` (Go), `py-spy dump --pid`, `kill -USR1` (Node w/ diagnostics), `gdb -batch -ex "thread apply all bt"`
- `ls /proc/$PID/fd | wc -l` and `lsof -p $PID` — fd/socket leaks
- `ss -tanp` — connection states
- `ps auxf` — leaked children
- `SELECT * FROM pg_stat_activity` and `pg_locks` (or `SHOW ENGINE INNODB STATUS`) — blocked queries, lock holders, *and whether the blocker belongs to another CI run*
- `docker logs` / `docker inspect` for every dependency container
- cgroup `memory.current` vs `memory.max`

One good stack dump usually collapses this entire list to a single answer in minutes. Everything else on this page is guessing.

## Discriminating experiments, cheapest first

1. Force unbuffered output — verify the "random position" claim is real.
2. Set an explicit pool acquire timeout — converts hang to stack trace, kills or promotes the pool theory.
3. Plot hang position across historical runs — uniform vs. back-loaded separates leaks from races.
4. Correlate hang times with concurrent CI runs — tests the shared-database theory using data you already have.
5. Run the suite with test parallelism set to 1 — if hangs stop, it's cross-test interference, not a single test.
6. Reproduce under CI's constraints locally: `docker run --cpus=2 --memory=2g`, same shuffle seed, same parallelism, in a 200-iteration loop. Then run two copies concurrently against one database.

My prior, given the specific combination of "integration tests only," "never locally," and 5%: shared external state contended between concurrent CI runs, or a thread-pool deadlock that only manifests at low core count. But I'd spend the effort on step 2 of the "actually ends this" section rather than on my prior — the stack dump is worth more than any amount of reasoning from the outside.