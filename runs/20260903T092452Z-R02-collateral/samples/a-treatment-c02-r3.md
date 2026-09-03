Don't try to settle this by argument. Change CI so that the hang produces a full stack dump of every thread instead of a timeout kill, then read the dump: almost none of the candidate explanations can be told apart without it, and the instrumentation costs an afternoon.

The most informative symptom you have is that it hangs at a different test each time, and the usual reading of it is backwards. It doesn't mean twenty tests are each subtly broken. It means the test where the run stops is the victim rather than the cause: something accumulates or races in the background, and whichever test happens to be running when it goes bad takes the blame. Per-test debugging is therefore a dead end, and so is quarantining "the flaky test." The second symptom, never reproducing locally, narrows what that background condition can be, because it has to be something CI does differently: stdout is a pipe rather than a TTY, the core count is lower, the cgroup CPU quota throttles, services run in containers over a real network, and the suite probably runs at a parallelism you never use.

On the connection pool theory, there is one cheap check that mostly settles it. A hang means something is waiting with no deadline. Resource exhaustion, by contrast, normally produces a loud error: a pool that runs out of connections raises a checkout timeout, and an exhausted ephemeral port range gives you `EADDRNOTAVAIL` rather than a wait. So go look at whether your pool has a finite acquisition timeout configured. If it does, exhaustion should be failing your tests, not freezing them, and the theory is close to dead. If it doesn't, the theory is live, and it also tells you that you have a second bug worth fixing regardless of what causes this one.

The candidates that actually fit "background condition, CI only, one run in twenty" are these, each with the signature that identifies it in a dump:

- **Subprocess pipe deadlock.** A test spawns a child with its stdout captured, then waits for it to exit without draining the pipe. The child fills the kernel's 64 KiB buffer, blocks on `write`, and the parent blocks on `wait` forever. This is the single best fit for "never locally," because locally the child's output often goes straight to your terminal. Whether the child crosses 64 KiB on a given run varies with retries and log verbosity, which gives you the one-in-twenty. In the dump: parent parked in `waitpid`, an orphan child still alive.
- **A socket read or queue get with no timeout.** A service drops a response, or a container dies, and the client waits indefinitely. In the dump: a thread in `recv`/`poll`/`Queue.get`, and often a dead or unhealthy container in `docker ps`.
- **A lock ordering deadlock that only opens under CI scheduling.** Fewer cores and more contention widen the race window. In the dump: two or more threads in `futex`/lock acquisition, with a cycle you can trace by hand.
- **Fork with threads.** A process forks while another thread holds an internal lock, typically the logging lock, and the child deadlocks the first time it logs. Common with Python's `fork` start method under parallel test workers. In the dump: a child process with a single thread parked acquiring a lock it can never get.
- **Genuine exhaustion.** File descriptors, threads, memory, or the pool. Distinguished by monotonic pressure across the run rather than a sudden stop.
- **Not a hang at all.** CPU throttling on a shared runner, or a retry storm with backoff, and the suite is merely crawling. Distinguished by whether CPU is pinned near zero or near the quota.

To tell them apart you want two artifacts. The first is a time series covering the whole run, so you see the run-up and not just the frozen endpoint; sample every ten seconds into a file you upload as a build artifact regardless of outcome:

```bash
while sleep 10; do
  date -Is
  ps -o pid,stat,wchan:24,pcpu,rss --ppid $TEST_PID --pid $TEST_PID
  ls /proc/$TEST_PID/fd | wc -l
  ss -tan | awk 'NR>1 {print $1}' | sort | uniq -c
  cat /sys/fs/cgroup/memory.current /sys/fs/cgroup/cpu.stat 2>/dev/null
done >> diag.log
```

A connection count or fd count that climbs monotonically and then plateaus at a round number is exhaustion, and it also tells you which resource. A count that is flat right up to the freeze is a race or a deadlock. CPU at zero means blocked on I/O or a lock, and `wchan` will say which; CPU pinned at the quota means a spin or retry loop. The `nr_throttled` field in `cpu.stat` tells you whether you are being throttled at all.

The second artifact is the stack dump at the moment of the hang, which means replacing the CI timeout kill with something that snapshots first. Use `timeout -s QUIT -k 30 25m ./run-tests.sh` where SIGQUIT already dumps, and arrange the runtime to cooperate: Go dumps every goroutine on SIGQUIT with `GOTRACEBACK=all` and does the same on its own `-timeout` (so never set that to zero); the JVM responds to `kill -3` or `jcmd <pid> Thread.print`; Node needs `--report-on-signal` and then SIGUSR2; Python wants `faulthandler.dump_traceback_later(300, repeat=True, exit=False)` in `conftest.py`, which prints all thread stacks periodically without killing anything, or `py-spy dump --pid` from outside, which needs no cooperation from the hung process at all. If you use `pytest-timeout`, prefer `--timeout-method=thread`, since the signal method can fail to fire on exactly the blocked-in-C cases you care about.

With those in place, force the issue rather than waiting a week for the next hang: run the integration suite twenty or thirty times in a loop in one CI job. At a one-in-twenty rate you get several dumps, and several dumps that all park in the same place is a far stronger signal than one. If you want it locally, the conditions worth copying are piping stdout to a file instead of a terminal, capping the container to one or two CPUs, and running at CI's worker count with the shuffle seed logged so a hang is replayable.