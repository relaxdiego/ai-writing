Your skepticism is worth taking seriously, and there's a two-minute check that either kills the pool theory or promotes it. But first, the two facts you gave constrain the space a lot.

**"Always a different test" means the test isn't the cause.** Whatever goes wrong is in shared state or the environment, and the victim is just whoever happens to be running when it tips over. That rules out a large family of bugs and points at: a resource that accumulates across tests, a lock held by something already finished, or an external dependency that stalls at an arbitrary moment.

**"Never locally" almost always means one of:** CI runs at different parallelism or on fewer cores (race windows widen enormously), CI captures stdout through a pipe instead of a terminal, CI has a container memory/CPU ceiling, or there's a NAT/firewall/load balancer between the runner and some service that your laptop doesn't have.

## Killing or confirming the pool theory

Pool exhaustion produces a *hang* only if the acquire path has no timeout. Most pools default to erroring out: SQLAlchemy's `pool_timeout` is 30s, HikariCP's `connectionTimeout` is 30s. If you're on one of those with defaults, exhaustion gives you a `TimeoutError` with a stack trace, not a hang — theory dead. But several common clients wait forever by default: `asyncpg.Pool.acquire()` (timeout `None`), node-postgres (`connectionTimeoutMillis: 0`), and Go's `database/sql` when you pass `context.Background()`. If you're on one of those, the theory is live — and the fix-and-diagnostic are the same thing: set a finite acquire timeout and the next hang becomes a stack trace pointing at the leak.

## The other real candidates

**A leaked transaction, not a leaked connection.** A test errors out mid-transaction, the connection goes back to the pool still `idle in transaction`, holding a row or table lock. The next test that touches that table blocks — and with `lock_timeout` unset in Postgres or a long `innodb_lock_wait_timeout` in MySQL, it blocks indefinitely. This fits "different test every time" better than pool exhaustion does, because the victim is whoever next touches the hot table. It also explains "never locally" if your local runs happen to be serial.

**A socket read with no timeout.** A connection gets silently dropped by a NAT or LB idle timeout; the client sits in `recv()` on a socket that will never produce bytes. Linux TCP keepalive doesn't fire for two hours, and only if `SO_KEEPALIVE` was set at all. Grep your codebase for HTTP calls with no timeout argument — `requests.get(url)` without `timeout=` is probably the single most common cause of infinite CI hangs in Python.

**Pipe deadlock on a subprocess.** A test spawns a child, the child fills the 64KB pipe buffer, and blocks because the parent isn't draining it while the parent waits on `wait()`. This is CI-specific by construction: locally your output goes to a terminal, in CI it goes through a pipe.

**Test-runner worker death.** With pytest-xdist, Jest workers, or JUnit parallel, a worker that dies without protocol cleanup (OOM kill is the usual reason) leaves the coordinator waiting forever. Check whether the runner's memory ceiling is close to your peak usage, and look for OOM kills in the runner logs.

**Cross-job collision.** If two CI jobs can land on the same runner and both bind a fixed port or use the same database name, one blocks. The 1-in-20 rate is suspicious here — it would track how often jobs overlap, not anything about your code.

## How to actually tell them apart

Stop reasoning about it and make the hang self-reporting. The single highest-value change: add a *test-level* timeout well below the CI job timeout that dumps stacks rather than killing the process. Python: `faulthandler.dump_traceback_later(300, exit=False)`, or `py-spy dump --pid` from a watchdog. Java/Go: send `SIGQUIT` for a thread/goroutine dump. Ordering matters — if the CI runner's own timeout fires first, it kills the job and you learn nothing.

Alongside the stack dump, capture `pg_stat_activity` (with `state` and `wait_event_type`), open FD count, `ss -tanp`, and your pool's checked-out count. Then the stack tells you which branch you're in: blocked in `acquire`/`getConnection` → pool; blocked in `recv` on an established socket with the DB showing nothing running → dropped connection; DB showing an `idle in transaction` session holding a lock → transaction leak; blocked in `waitpid` with a full pipe → subprocess deadlock; no stack at all because the process is gone → OOM.

Two cheap things to do while you wait for the next failure. **Record where in the run each hang occurs** — test index and wall-clock offset. If it clusters at a consistent depth, something accumulates monotonically (leak). If it's uniformly scattered, it's a race or an external stall. That one bit separates half the candidates. **Then run the suite serially in CI** for ~40 runs. If the hang vanishes, it's cross-test interference — pool, locks, or ports. If it survives, it's per-test external I/O, and you're looking at timeouts on network calls.

If you tell me the language and DB client, I can narrow which of these are actually reachable for you.