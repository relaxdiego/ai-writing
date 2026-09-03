Your skepticism is well-founded. The signature you're describing — random test, 1-in-20, CI-only — actually argues *against* straightforward pool exhaustion, for a specific reason: a leaked-connection bug is **cumulative and deterministic**. If each of N tests leaks one connection from a pool of 10, you hang on the 11th test, every time, same place. The fact that it moves means either the leak itself is racy, or it isn't a leak at all.

## The one thing worth more than all the theorizing

Get a stack dump of the hung process. Everything below is inference; a stack trace is evidence. Right now your CI almost certainly kills the job at the timeout and throws away the only interesting state in the whole system.

Add a watchdog that fires *before* the job timeout and dumps, rather than kills:

- **JVM** — `kill -QUIT` (thread dump to stdout), or `jcmd <pid> Thread.print`
- **Go** — `kill -QUIT` with `GOTRACEBACK=all`, or hit `/debug/pprof/goroutine?debug=2`
- **Python** — `py-spy dump --pid <pid> --native`, or arm `faulthandler.dump_traceback_later(600)` in a conftest fixture
- **Node** — `--report-on-signal` then `kill -USR2`, or `SIGUSR1` + inspector
- **Ruby** — `rbspy dump`; **.NET** — `dotnet-dump`

Grab the environment at the same moment: `ss -tanp` (socket states — `SYN-SENT` vs `ESTABLISHED` vs `CLOSE-WAIT` piles is enormously diagnostic), `ps -eLf`, `lsof -p`, and on the DB side `pg_stat_activity` / `SHOW FULL PROCESSLIST`.

Then compare stacks across several hangs. **Same stack shape at different tests → one shared bug in common infrastructure. Different stacks → a resource-level problem.** That single fork cuts the space in half.

## The realistic hypothesis space

**Missing I/O timeouts.** The most common root cause by far. Some socket read, HTTP client, or DB call has no timeout, so *any* transient hiccup becomes an infinite wait. The trigger is random, hence the random test. Locally, nothing ever hiccups. Tell: stack sits in `read`/`recv`/`poll`, socket in `ESTABLISHED` with no traffic.

**Silently dropped packets.** CI networks (security groups, NAT gateways, egress firewalls) drop rather than reject. A `connect()` to a blocked address doesn't fail — it retries for minutes, sometimes forever. Tell: socket in `SYN-SENT`.

**Blocked on a full stdout pipe.** Genuinely underrated and *perfectly* explains "never locally." CI captures output through a pipe; if the consumer stalls or a subprocess inherits the pipe and nobody drains it, the 64KB buffer fills and the writer blocks in `write()` forever. Locally you have a terminal, so it never happens. Tell: stack in a write to fd 1/2, or the log tail cuts off mid-line.

**Thread/executor pool deadlock.** Test thread blocks on a future scheduled onto a pool that's saturated, or has no threads left because earlier work is itself blocked. Cousin of pool exhaustion but a different fix. Tell: all worker threads parked, one main thread in `Future.get`.

**Cross-test state leakage.** Test A poisons a shared resource (leaves a transaction open holding a row lock, doesn't close a container, binds a port); whichever test touches it next hangs. Location is random, but the *culprit* is fixed. Tell: hang correlates with a specific *predecessor*, and the DB shows `idle in transaction` or a lock wait.

**Timing amplification.** CI runners are CPU-throttled by cgroup quota and shared with neighbors. A 50ms window becomes 5s, and a latent lost-wakeup or wait-before-signal race starts landing. Tell: hangs correlate with runner load or specific runner IDs.

**Not actually hung.** A retry ladder with exponential backoff can take 40 minutes. You'd never know, because you kill it at 20. Cheap to check: raise one job's timeout to 3× and see if it eventually passes.

## Experiments, cheapest first

1. **Set a short pool acquisition timeout (5–10s).** This is the single best experiment. If it *is* the pool, the hang converts into a loud exception with a stack trace pointing at the leak. If nothing changes, you've eliminated the hypothesis for the cost of one config line. Do this before anything else.
2. **Set aggressive timeouts on every network client** — connect, read, statement, request. Same logic: turn a hang into a failure with a stack. You want these in production anyway.
3. **Move the pool size.** Drop to 1–2: if pool-related, the failure rate spikes and it may reproduce locally. Raise to 100: if it vanishes, that's strong confirmation. Either direction is informative.
4. **Set test parallelism to 1.** Still hangs → the bug is *within* a test. Stops → cross-test interference or contention.
5. **Loop the suite 100× on a CI runner** (not locally) under `stress-ng --cpu` or `docker run --cpus=0.5`. Amplifying timing skew is usually what closes the local/CI reproduction gap.

## Make the next hang free

Whatever you do, instrument every run to record: hanging test name, **its ordinal position in the run**, worker index, runner ID, test order seed, wall-clock time, and preceding test per worker.

The ordinal distribution alone settles the pool question. **Uniform across the run → not cumulative, so not exhaustion. Skewed toward the end → cumulative resource consumption, and your colleague is probably right.** Twenty hangs at one-in-twenty is 400 runs, which is a week or two of normal CI traffic — you'll have an answer without doing anything heroic.

---

If you tell me the language/runtime, what the integration tests actually talk to (real DB? testcontainers? external services?), and whether CI runs them in parallel, I can narrow this considerably and give you concrete instrumentation code rather than a menu.