Your skepticism is half right. Connection pool exhaustion is a plausible member of the right family, but the family is larger than that one member, and "always a different test" is the clue that tells you which family you're in rather than which member.

A test that hangs in its own logic hangs at the same place every time. Yours doesn't, so either something accumulates across the run and tips over at whatever test happens to be executing when the threshold is crossed, or something in the environment lands at an arbitrary point in wall-clock time. A leaked connection is the first kind: the test that hangs is simply the one that asked for connection N+1, and its identity is an accident. But a leaked semaphore permit, a fixed-size thread pool where a queued task waits on another task in the same pool, or an unclosed transaction all produce the same signature. So does the second kind, for entirely different reasons.

The candidates I'd actually weigh, given that it reproduces only in CI:

Shared-database lock contention is the one I'd suspect first if your integration tests run in parallel workers against a single database. Postgres will break a true deadlock, but it will not break a plain lock wait; a `SELECT FOR UPDATE` sitting behind a session that's idle in transaction waits forever unless you've set `lock_timeout`. Locally you probably run serially, so the contention never arises. Test-order randomisation makes this look non-deterministic even when it's a deterministic interaction between one pair of tests.

Missing socket timeouts are next. On your laptop the dependency is on loopback and either answers or refuses immediately. In CI a container can be scheduled, DNS-resolvable, and still black-hole your SYN or accept the connection without ever serving it. With no connect or read timeout configured, that's an unbounded block, and the randomness comes from container startup ordering rather than from your code.

Parallelism and sizing differences deserve attention because they explain "never locally" without requiring any behavioural difference at all. Many pool libraries size themselves from CPU count, so a pool that's comfortably large on your ten-core machine is starved on a two-vCPU runner, and the same leak that is invisible locally becomes fatal in CI at one run in twenty.

The dark horse is output backpressure. If the job captures stdout through a pipe that nothing is draining, a process writing verbose logs blocks on `write` once the buffer fills, and that presents exactly as a hang at an arbitrary test.

To tell these apart, stop letting the platform kill the job and make the hang produce an artifact instead. Set a per-test timeout well below the job timeout, and on expiry dump every thread's stack: `faulthandler.dump_traceback_later` in Python or `py-spy dump`, `jstack` or `SIGQUIT` on the JVM, `SIGQUIT` for Go, active handles for Node. One such dump usually collapses this entire list to a single candidate, because a parked thread names its own reason for parking. Alongside it, capture:

- `pg_stat_activity` with `state`, `wait_event_type`, `wait_event` and `query_start`, plus `pg_locks`, so a lock wait or an idle-in-transaction session identifies itself
- your pool's in-use, idle and waiting counts, logged after every test, since a monotonic climb across the run is the leak signature and confirms or kills the pool theory in one run
- the random seed and the resulting test order, printed unconditionally
- worker count, `nproc`, and the pool's configured maximum

The predictions then separate cleanly. If it's a leak, the ordinal position of the hang stays roughly constant while the test name varies, and the pool counts climb. If it's an order-dependent interaction, replaying the recorded seed reproduces it, which also gives you a fast bisect. If it's infrastructure, the hang correlates with a slow dependency rather than with anything in the suite. And if serial single-worker runs in CI never hang while parallel ones do, everything network-related drops away and you're looking at shared state or contention.

The seed logging and the stack dump on timeout are worth doing before any further theorising; one in twenty means roughly two or three runs to catch it, and you'd rather spend those runs collecting evidence than confirming a guess. Happy to look at the CI config and the fixture setup if you want to point me at them.