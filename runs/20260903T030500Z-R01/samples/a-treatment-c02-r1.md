Your skepticism is well-placed, though the answer is probably in the neighborhood of the pool theory rather than far from it.

## What the pattern already tells you

Three facts constrain this a lot:

**"Always integration tests"** means the process is blocked on something external — a socket read, a pool/semaphore acquire, or a server-side lock. In-process deadlocks (a mutex, an executor) can happen in unit tests too; the fact that it never does says the wait is on a resource that lives outside your process.

**"Always a different test"** is the strongest signal, and it argues against the victim test being the culprit. When the failing test moves around, the usual structure is a *poisoner* and a *victim*: some earlier test leaves shared state broken, and whichever test next touches that state is the one that hangs. The victim looks random because it depends on ordering, timing, or which xdist worker drew the bad connection.

**"1 in 20, never locally"** means it needs a race or an environment delta, not just accumulation. A plain connection leak is monotonic and deterministic — you'd hang at roughly the same depth in nearly every run, not 5% of them.

## The candidates that fit

**Leaked transaction or lock from an earlier test.** A test hits an error path, its connection goes back to the pool with an open transaction, and Postgres holds the row/table locks. The next test that touches that table blocks — and by default blocks *forever*, because `lock_timeout` is 0. Fits every part of your pattern: random victim, low rate (only when the poisoner's error path fires), never locally (locally you probably run serially against a fresh DB).

**Concurrency shape differs in CI.** Your laptop has 8–12 cores; the runner has 2. Anything sized off `cpu_count` shrinks: default thread pools, xdist workers, sometimes the DB pool itself. A deadlock that requires more concurrent waiters than pool slots simply cannot happen on your machine and happens routinely on the runner.

**A socket with no timeout, and a peer that vanished.** In CI the DB is a sidecar container behind a bridge network; it can get OOM-killed, or a conntrack entry can expire mid-connection. A blocking `recv()` with no `SO_KEEPALIVE` and no socket timeout waits indefinitely on a dead connection. Locally you're on loopback, which never does this.

**Actual pool exhaustion** — plausible only in the form where the pool has no acquire timeout. But it's the same fix path as the first item, and the diagnostics below separate them in one shot.

Underneath all four: **a hang instead of a failure is itself a bug in your timeout configuration.** Whatever the trigger, something in the stack has an unbounded wait. That's worth fixing independently of the root cause, and doing so is also how you diagnose it.

## How to tell them apart

**Get a stack dump from the hung process.** This is worth more than everything else combined, and all four hypotheses look completely different in a stack. Add to `conftest.py`:

```python
import faulthandler
faulthandler.dump_traceback_later(300, exit=True)  # well under the CI job timeout
```

or use `pytest-timeout --timeout=300 --timeout-method=thread`, which dumps every thread's stack. Then read the bottom frame:

- `socket.recv` / `poll` → network black hole or a dead peer
- `pool.acquire` / `Semaphore.acquire` → exhaustion, client-side
- `libpq` waiting inside an ordinary query → server-side lock contention
- `future.result()` / `Lock.acquire` → executor or in-process deadlock
- `subprocess` pipe read → runner plumbing, not the DB at all

Set the timeout comfortably below the CI job limit, or the runner kills you before the dump lands.

**Dump server state at the same moment.** In the same watchdog, or as a CI step that fires on timeout:

```sql
SELECT pid, state, wait_event_type, wait_event, xact_start, query
FROM pg_stat_activity ORDER BY xact_start;
```

Twenty connections `idle in transaction` is the leak. A row in `active` with `wait_event_type = 'Lock'` is contention. Connections at exactly your pool ceiling with your app blocked before it ever issued a query is real exhaustion. This single query separates the top three hypotheses.

**Falsify the pool theory cheaply.** Set `pool_timeout=10`. If exhaustion is the mechanism, the hang converts into a prompt `TimeoutError` on most runs — confirmed, with a stack trace naming the test. If it still hangs, the wait is downstream of the pool and you can drop the theory. Shrinking the pool to 1 is the aggressive version: if it's exhaustion you'll now reproduce it constantly.

**Check whether it's ordering-dependent.** If you use `pytest-randomly` or xdist, log the seed on every run. When a run hangs, replay that exact seed. Reproducing means it's a pairwise interaction, and you can then bisect the test list down to the poisoner in ~7 runs. Not reproducing points at genuine timing or network flake. Separately, run the suite with `-n0` in a loop of 100 — if the hang vanishes without parallelism, the shared resource is being contended, not leaked.

**Reproduce the environment, not the code.** Run your CI image locally with `--cpus=2 --memory=2g` and loop the suite overnight. A surprising share of "never happens locally" hangs are purely a core-count effect on default pool sizing.

## Regardless of what you find

Set `lock_timeout`, `statement_timeout`, and especially `idle_in_transaction_session_timeout` on the CI database. The last one turns a leaked transaction from a silent hang into a loud, attributable error at the leak site rather than at some innocent test twenty minutes later. Add socket timeouts and TCP keepalives on every client. Once nothing in the stack can wait forever, this class of bug stops presenting as a hang and starts presenting as a flaky failure with a stack trace — which is a problem you can actually work on.