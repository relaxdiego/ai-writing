Your instinct to push back is right — not because pool exhaustion is implausible, but because the symptom pattern is generic enough that a dozen causes fit it equally well, and one of them (a missing timeout) is guaranteed to be present regardless of which is the real trigger.

## What the symptoms already narrow down

**"Always a different test"** means the hanging test is almost certainly a victim, not a culprit. Something is either accumulating across the run (a leak crossing a threshold) or racing between concurrent workers, and whichever test happens to be running when the condition trips takes the blame. Stop bisecting individual tests.

One caveat: verify the reported test is really where it stopped. If your CI output is block-buffered rather than line-buffered, the last flushed line can lag the actual position by a lot, and "different test each time" would partly be log noise.

**"Hangs" rather than "fails"** is the sharpest clue. Something is blocked on a wait with no deadline, or a deadline longer than the job timeout. That's a defect independent of root cause — the underlying race might be unavoidable, but it should surface as a 30-second failure with a stack trace, not a 60-minute stall.

**"Never locally"** usually reduces to three differences: parallelism (CI runs N workers against one shared database), resource limits (cgroup CPU/memory caps that change thread-pool sizing and scheduling), and fresh short-lived containers (services that restart, get OOM-killed, or aren't actually ready when the port opens). Locally you have warm services, spare CPU, and often fewer workers.

## The realistic candidates, ranked

1. **Cross-worker database lock contention.** Two parallel workers touch the same rows, or one truncates a shared table while another holds a transaction open. Postgres has *no* default lock timeout, so this waits forever. (MySQL's `innodb_lock_wait_timeout` defaults to 50s, so it errors instead — which is why this hypothesis is much stronger on Postgres.) A leaked open transaction from a test that failed mid-way is the usual initiator.

2. **A silently dead peer.** A service container restarts or gets OOM-killed without a clean FIN/RST; or a cloud NAT/LB drops an idle flow at ~350s. The client socket stays `ESTABLISHED` and `read()` blocks until TCP keepalive fires — 2 hours on default Linux. Absolutely looks like an infinite hang, and is a top cause of "only in CI."

3. **Connection pool exhaustion.** Genuinely fits "different test each time" (leak accumulates, whoever crosses the ceiling blocks) and "not locally" (shared ceiling across workers). But it only produces a *hang* if pool acquire has no timeout — most pools default to a finite one and raise. Check that config; it's a two-minute check that promotes or nearly kills the theory.

4. **Thread-pool / event-loop deadlock.** All N pool threads blocked awaiting work that must run on the same pool. CPU-throttled CI makes the bad interleaving far more likely than an unconstrained laptop.

5. **Pipe deadlock.** A test spawns a subprocess, doesn't drain its stdout, the 64 KiB pipe buffer fills, the child blocks on `write()`, the parent blocks in `wait()`. Doesn't reproduce locally because a TTY changes buffering and local runs are often quieter.

6. **Container-level resource exhaustion.** Memory cgroup kills the DB or a helper; fd or disk exhaustion on a shared runner. Test then waits on something dead.

7. **Cross-test state contamination** — a frozen clock or global monkeypatch a crashed test never undid, so a background poller never wakes.

## The one move that collapses all of this

Make the hang report on itself, then let it happen once.

Set an internal watchdog *below* the CI job timeout, so your process dumps state before the runner kills it — CI systems frequently skip post-steps on job timeout, so an external "collect diagnostics on failure" step often never runs.

- **Go**: the test binary's own timeout already panics with all goroutine stacks.
- **Python**: `faulthandler.dump_traceback_later()`, or `pytest-timeout` with `method=thread`.
- **JVM**: `jcmd <pid> Thread.print` (or SIGQUIT).
- **Node**: SIGUSR1 to open the inspector; `why-is-node-running` for stragglers.

Alongside the stack dump, capture in one script: `ss -tanp` (socket states plus Send-Q/Recv-Q and timers), `ps -eLf`, `dmesg -T | tail`, container restart counts and `OOMKilled` flags, cgroup `memory.current`, `df -h`, pool in-use/idle/waiting counters, and on the DB side `pg_stat_activity` (`state`, `wait_event_type`, `wait_event`) plus `pg_locks WHERE NOT granted` — or `SHOW ENGINE INNODB STATUS` for MySQL.

## Reading the evidence

- Every stack in `pool.acquire` **and** in-use == max → pool exhaustion. Confirmed, not guessed.
- Pool has idle capacity but a query is stuck, DB shows `wait_event_type = Lock` → lock contention between workers.
- Client socket `ESTABLISHED` but the DB/service has **no** matching session, or the peer container's restart count is nonzero → dead peer, missing socket timeout.
- All executor threads blocked in `await` with a non-empty queue → thread-pool deadlock.
- Child in `D`/blocked writing to a pipe, parent in `wait()` → pipe deadlock.
- Process gone, exit 137, OOM lines in `dmesg` → memory limit.

## Experiments that narrow it without waiting on luck

**Mine your existing logs first — no new runs needed.** For the last ~20 hangs, record elapsed time into the run, worker ID, runner host, and the preceding few tests. A pool or resource leak predicts a *late skew*. A bad runner predicts host clustering. If ordering is randomized, look for a common predecessor within a few tests of the hang — that's your real culprit.

**Then amplify.** Run the integration suite 50× in a loop on a branch. At 1-in-20 that's ~2–3 reproductions, and it gives you a feedback loop for testing fixes. Change one knob per loop:

- `-p 1` (serial). If the hang vanishes, it's inter-worker interaction, not a single test's bug.
- Raise pool max 10×. If it vanishes, the pool theory survives; if not, it's mostly dead.
- Fix the ordering seed. Reproducible order → bisectable.
- Set aggressive timeouts everywhere. This converts the hang into a failure with a stack trace, which is both the diagnostic and the permanent fix.

**And try harder to reproduce locally**: same image, `--cpus=2 --memory=2g`, same worker count, 100 iterations. Most "never locally" is just resource limits plus parallelism.

Two checks worth doing regardless of what you find: assert `pool.in_use == 0` at the end of every test (this fails at the *culprit* rather than the victim), and put a deadline on every blocking wait — socket connect/read, pool acquire, HTTP client, plus `statement_timeout` and `lock_timeout` on the database. Once nothing can block forever, a 1-in-20 hang becomes a 1-in-20 failure with a stack trace, and you'll have it in a single run.

If you point me at the repo and a couple of hung-run logs, I can look at the actual pool config, timeout settings, and fixture/parallelism setup rather than reasoning from the outside.