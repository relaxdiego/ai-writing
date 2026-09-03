Before ranking hypotheses, be suspicious of your main piece of evidence: "always at a different test" is what you'd also see if the output were buffered and the hang location had nothing to do with the last line printed. The first move is not to reason about causes but to make a hung run dump stacks before CI kills it.

That matters because the frequency signature is doing more work than the location signature. One run in twenty, spread over arbitrary tests, is what a constant per-unit-time hazard looks like: some rare background event fires, and it catches whichever test happened to be running. A bug in a particular test would cluster. An accumulating resource leak would bias late in the run, since the pool doesn't run dry in the first thirty seconds. So already there are three distinguishable shapes, and you can measure which one you have from the logs of hangs you've already collected: record hang position as a fraction of the suite (test index at hang divided by total), and look at the distribution across your twenty-odd historical failures. Uniform points at an external event; late-biased points at exhaustion or a leak; a cluster points at a specific test whose neighbours vary because of ordering.

The candidates that fit "hangs rather than fails, only in CI, at random":

- **A rare external event plus a client with no timeout.** A service container restarts, gets OOM-killed, or a packet is dropped, and the test blocks forever on a socket read that has no deadline. The event is rare; the missing timeout turns it from a retry into a hang. Tell: exit code 137 somewhere, OOM lines in `dmesg`, non-zero restart counts on the service containers, a thread parked in `recvfrom` on an ESTAB or SYN_SENT socket.
- **Thread-pool or event-loop starvation sized from CPU count.** CI gives you two cores under a cgroup quota; your laptop has ten or sixteen. Default pool sizes derived from core count get small enough that every worker ends up blocked on I/O whose completion needs a worker. Never reproduces locally because the pool is never that tight. Tell: all pool threads in blocking calls with a non-empty work queue.
- **Test-runner parallelism with a dead worker.** A worker process is OOM-killed or segfaults, and the coordinator waits forever for a result that will never arrive. Tell: fewer worker PIDs alive than configured, coordinator parked in `waitpid`, `select`, or a queue read.
- **Pipe deadlock on stdout.** In CI the process writes to a pipe with a 64K buffer, not a TTY. A child that logs heavily fills the buffer, the parent isn't draining it, and both block. Tell: writer blocked in `write()` on a pipe, and the hang reproduces locally the moment you redirect output to a file instead of a terminal.
- **Lock waits with no timeout.** Postgres advisory locks, a fixture that TRUNCATEs while another test holds a row lock, `BLPOP key 0` against Redis, a mutex held across an exception path. Deadlock detection catches the cycles, but a plain wait on a lock nobody will release is not a cycle. Tell: `pg_stat_activity.wait_event_type = 'Lock'` and a `pg_locks` graph showing the blocker.
- **Connection pool exhaustion.** Real, but with a specific signature, and it usually errors rather than hangs unless the checkout call has no timeout configured. A leak also ramps monotonically, so it should bias late.
- **Not hanging in a test at all.** The suite finished and the process won't exit, because a non-daemon thread, an open handle, or a pending timer keeps the runtime alive. Cheap to rule out: compare the number of tests reported to the number collected.

The single diagnostic that discriminates almost all of these is a stack dump of every process and thread at the moment of the hang. Replace CI's blunt job timeout with a watchdog that collects state first:

```bash
./run-integration-tests & SUITE=$!
( sleep "${SUITE_TIMEOUT:-1800}"
  kill -0 $SUITE 2>/dev/null || exit 0
  echo "=== suite hung, collecting ==="
  ps -eLf                                  # every thread and its state
  for p in $SUITE $(pgrep -P $SUITE); do
      py-spy dump --pid "$p"               # or: kill -QUIT (JVM, Go), eu-stack -p
      cat /proc/$p/status 2>/dev/null
  done
  ss -tanp                                 # ESTAB / SYN_SENT / CLOSE_WAIT counts
  dmesg | tail -50                         # OOM kills
  psql -c "select pid,state,wait_event_type,wait_event,left(query,60)
           from pg_stat_activity"
  kill -ABRT $SUITE
) & WATCHDOG=$!
wait $SUITE; kill $WATCHDOG 2>/dev/null
```

Archive that output plus the run's random seed and worker assignment. One captured hang will usually name the culprit outright: a thread in `pool.acquire` is the pool hypothesis, a thread in `read` on a socket is the timeout hypothesis, a missing worker with a coordinator in `waitpid` is the OOM hypothesis.

You can also test the pool suggestion directly in a single run, without waiting for a hang. Set the pool checkout timeout to five seconds. If exhaustion is the cause, the hang converts into a clean error that names the pool and prints a stack at the point of checkout; if the run still hangs silently, the suggestion is wrong and you've spent one CI run to retire it. Alongside that, log checked-out connection count per test. A leak shows as a staircase that never comes down, which is visible long before it becomes fatal.

For local reproduction, the thing to copy is not the code but the constraints. Run the same container image under `docker run --cpus=2 --memory=2g`, with stdout redirected to a file rather than a terminal, in a loop of fifty. The CPU limit exercises the pool-sizing and starvation candidates, the memory limit exercises the OOM candidate, and the redirect exercises the pipe candidate. If it reproduces once you've matched those three, you have it on a machine where you can attach a debugger. If fifty constrained runs stay clean, that's evidence for the external-event family, and the next place to look is the CI network path: retransmit counters in `netstat -s`, conntrack table pressure, and whether your DNS resolver has a bounded timeout.