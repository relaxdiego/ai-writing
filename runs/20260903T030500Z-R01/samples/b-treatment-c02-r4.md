Your skepticism is well-placed, but not for the reason you might think — pool exhaustion is actually consistent with "different test each time." What makes it only one hypothesis among several is that the observable evidence you have so far doesn't discriminate between any of them.

## What the pattern already tells you

"Always integration tests, always a different test" rules out a single broken test and points at something *shared* — state that accumulates across tests, or a resource contended by things outside the test process. The victim is whichever test happens to be running when the shared thing goes bad, which is why it looks random.

"Never locally" narrows it further. The differences that matter are almost always: fewer CPUs (or a cgroup quota), parallel workers sharing one database, a network path with NAT/proxy in it, output going to a pipe instead of a terminal, and containerized service dependencies that start in a different order.

"One in twenty" tells you it's a race or a threshold effect, not a deterministic bug.

## The candidates

**Resource exhaustion (pools, file descriptors, DB connections).** A leak on some conditional path — an error branch that skips cleanup, a transaction never rolled back. The hang happens when the pool is finally drained. Signature: the hang position correlates with *how many* leak-triggering tests have run, not with which test. Also, most pools have an acquire timeout, so a true hang means either the timeout is unset/infinite or something's holding a connection open indefinitely.

**Stale connection with no read timeout.** Related but different, and my personal favorite for CI-only hangs. A NAT gateway, load balancer, or conntrack table silently drops an idle connection without sending a RST. Your client pulls it from the pool, writes, and blocks on read forever. Locally there's no middlebox, so it never happens. Signature: hang always follows an idle gap in the suite; TCP keepalive disabled; `ss -tanp` at hang time shows an ESTABLISHED socket with a non-empty send queue.

**Database lock contention.** Parallel CI workers against a shared database, two tests grabbing the same rows in opposite order. Locally you run one worker or a fresh DB per run. Signature: `pg_stat_activity` / `SHOW ENGINE INNODB STATUS` at hang time shows blocked queries. Deterministic to check, and cheap.

**Async race that only loses under load.** A listener registered after the event fires, a condition variable signaled before the wait starts, an awaited promise that never settles. Constrained CPU changes the interleaving. Signature: no network or DB activity at all at hang time; the stack sits in a wait primitive.

**Thread/worker pool starvation.** Node's libuv pool defaults to 4 threads and gets eaten by DNS and crypto; connection pools sized for a dev box exceed CI's limits; a blocking sync call on the event loop. Signature: work queued but no threads available, and it correlates with CPU count.

**Blocked subprocess pipe.** If your integration tests spawn a service as a child process and you don't drain its stdout, it blocks on a full 64KB pipe buffer once it's written enough, and the parent waits forever for output that will never come. Very CI-specific, because CI usually runs things with verbose logging enabled.

## How to actually tell them apart

Stop reasoning about which is likelier and make the next hang produce evidence. This is a one-time instrumentation cost and it collapses the whole list.

Set a **per-test timeout below the CI job timeout**. Right now the job timeout almost certainly kills everything and gives you nothing. On that timeout, dump:

- **All thread/goroutine/async stacks.** `SIGQUIT` for Go, `jstack` for JVM, `py-spy dump --pid` for Python, `SIGUSR1` plus inspector or `process._getActiveHandles()` for Node. This single artifact usually identifies the culprit outright — you see whether you're blocked in `pool.acquire`, `socket.read`, `futex_wait`, or `waitpid`.
- **`ss -tanp`** — established sockets, send/recv queue depths, which peer.
- **Server-side session state** — `pg_stat_activity` with `wait_event_type` and `state`, or the equivalent.
- **`lsof -p`** — fd count against the limit.

Then add two cheap discriminators. Log **the ordinal position of each test and the wall-clock time**; across several hangs, check whether it's the same index-ish every time (accumulation) or uniformly spread (race). And run one CI job with **`--workers=1`**: if the hang disappears, it's cross-worker contention on the shared database or a shared fixture, not an in-process leak.

For reproduction, the loads that matter are CPU quota and parallelism, not machine size — run the suite in a loop under `docker run --cpus=2 --memory=2g` with the same worker count and the same verbose logging CI uses. That reproduces a surprising share of "CI-only" hangs on a laptop.

If you want to bound the damage while you investigate: set explicit timeouts on every pool acquire, socket read, and HTTP request, and enable TCP keepalive. That converts the hang into a fast, attributable failure with a stack trace — which is often enough to find the bug on its own.