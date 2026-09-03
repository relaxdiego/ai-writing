## What the symptom signature already tells you

Three facts constrain this a lot more than they look:

**"Always a different test"** — the hang is almost certainly *not* caused by the test it hangs on. That test is just where a poisoned or contended resource happened to get touched. This immediately demotes "a specific test has a bug" and promotes accumulating state, cross-test interference, or an environmental condition that fires probabilistically.

**"Never locally"** — the trigger is something CI has that your laptop doesn't. The usual suspects: fewer cores (a container capped at 1–2 CPUs vs. your 10), output captured through a pipe instead of a TTY, real network paths with NAT/conntrack instead of loopback, cold caches and slower service startup, different base image (Alpine's musl resolver behaves very differently from glibc), and CPU steal from noisy neighbors.

**"About 1 in 20"** — frequent enough to stress-reproduce. 100 loop iterations gets you ~5 hangs. That is an entirely tractable experiment, and it's the single highest-leverage thing you can set up.

## Why the pool theory is under-determined

The connection-pool story isn't crazy, but it's being asserted without the evidence that would distinguish it, and it makes a testable prediction that people rarely check.

If it's a genuine leak, the hang should be **biased toward late in the run** — each leaked connection makes the next test more likely to be the one that blocks. If your hang positions are actually uniform across the suite, a monotonic leak is a poor fit; you're more likely looking at a race that's equally likely at any moment.

More importantly: pool exhaustion only produces a *hang* if the acquire has no timeout. Set `acquireTimeout`/`checkout_timeout`/`connectionTimeout` to something finite and the hypothesis dies or confirms itself in one run — you either get a clean "timed out waiting for connection from pool" with a stack trace, or you don't, and it was never the pool.

## The realistic candidate list

**Blocked-forever waits (the biggest family).** Anything with a default of "wait indefinitely": pool acquire, socket read, HTTP client, DB lock. Postgres in particular has `lock_timeout` and `statement_timeout` off by default, so one test leaving an uncommitted transaction holding a row lock will make an unrelated later test block forever, with no deadlock detector firing (it's a wait, not a cycle).

**Thread/executor pool starvation.** Sync-over-async, a blocking call inside an async handler, or a task waiting on a future scheduled behind it. This is exquisitely sensitive to core count — a pool sized `nproc` deadlocks at 2 cores and never at 10. Best single explanation for "never locally."

**Pipe buffer deadlock.** A subprocess writes to stdout, the parent isn't draining, the ~64KB pipe fills, the child blocks on write forever. CI captures output through a pipe; your terminal doesn't. Random test = whichever one happened to be verbose enough to cross the threshold that run.

**Silently dropped connections.** NAT/conntrack or a cloud LB reaping an idle TCP connection without sending RST. The client's `read()` never returns and never errors. Loopback never does this to you locally. TCP keepalive or a socket read timeout is the fix and the test.

**Test-order / shared-state race.** If your runner randomizes or shards, a hidden inter-test dependency gives you exactly this profile. Check whether the seed is logged — if it isn't, fix that first.

**Port/listener collisions.** A stub server from a previous test that didn't shut down, or two shards binding the same port, so a request goes somewhere that will never answer.

**Not actually hung.** Check whether CPU is pegged or idle at hang time. Pegged = livelock or infinite retry loop; idle = genuine block. This one observation splits the space in half.

## Make the hang produce evidence

Right now a hang gives you nothing but a job timeout, which is why you're arguing from priors. Change that first — it typically ends the debate on the very next occurrence.

- **Per-test timeout well under the job timeout**, configured to dump rather than kill. Python: `faulthandler.dump_traceback_later()` or `pytest-timeout` with `--timeout-method=thread`. JVM: `jstack` / `kill -3`. Go: `GOTRACEBACK=all` + SIGQUIT. Node: `why-is-node-running` or an `async_hooks` dump. Ruby: iterate `Thread.list` and print backtraces.
- **On timeout, also snapshot the environment**, not just the process: `pg_stat_activity` and `pg_locks` (or your DB's equivalent), `ss -tanp` for socket states, thread count, pool gauge metrics.
- **Upload those as CI artifacts on failure**, and make sure the job's cleanup step doesn't discard them.
- **Log the run seed, shard assignment, and test index** so you can compare hang positions across occurrences.

## Discriminating experiments

| Hypothesis | Prediction if true | Cheapest test |
|---|---|---|
| Pool exhaustion / leak | Hang position skews late; pool gauge at max | Set finite acquire timeout; graph pool checkouts over the run |
| DB lock wait | One session `idle in transaction`, another `waiting` | Set `lock_timeout`; dump `pg_locks` at hang |
| Executor starvation | Reproduces under CPU limits, not otherwise | Run locally with `--cpus=1` or force pool size to 2 |
| Pipe buffer deadlock | Hang correlates with verbose tests; child blocked in `write` | Redirect subprocess output to a file instead of a pipe |
| Dropped TCP connection | Socket in `ESTABLISHED` with no traffic; thread in `recv` | Enable TCP keepalive; set socket read timeouts |
| Ordering race | Reproduces on replay of the same seed | Re-run the recorded seed; then run `-j1` serially |
| Livelock / retry loop | CPU pegged during hang | `top` on the runner mid-hang |

## Suggested order

1. Add the timeout-plus-stack-dump instrumentation and artifact upload. Ship it before doing anything else.
2. Set every infinite wait to something finite — pool acquire, socket connect/read, DB statement and lock. This converts hangs into stack traces, and *which* timeout fires names the layer.
3. Stress-run: the CI image, in a loop, with the same CPU and memory limits as the runner. If it reproduces under `--cpus=1` but not unconstrained, you have your answer already.
4. Run serially. If `-j1` never hangs across many iterations, it's a concurrency race; if it still hangs, look outward at the environment and external services.

If you tell me the language, test runner, and datastore, I can narrow the instrumentation to the exact flags and the two or three hypotheses that actually apply to that stack.