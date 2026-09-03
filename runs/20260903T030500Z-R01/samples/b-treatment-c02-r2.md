A few things in your description are doing more work than they look.

**"Always a different test" means the hanging test is probably the victim, not the culprit.** A test that hangs on its own would hang in roughly the same place every time. Random placement points at either shared state that accumulates across tests, or a timing-dependent condition that any test can trip.

**"Never locally" is a statement about the environment, not the code.** The interesting question is which specific difference matters. Usually it's one of: CI runners have a CPU quota (often a fraction of a core under cgroups) so everything is slower and reordered; CI captures stdout through a pipe rather than a TTY; service dependencies are separate containers over a network instead of localhost; the database starts empty and cold; parallelism or shard count differs from your local default; and other jobs may be contending for the same runner or the same external resources.

### The candidate families, and what each predicts

**Cumulative resource leak** (connection pool exhaustion, file descriptors, ephemeral ports, threads). Predicts hangs skewed *late* in the run, and if the leak is one-per-test, at roughly the *same* position each time. Your randomness argues against the simple version — it would only fit if the leak is itself conditional, e.g. a connection only leaks on the error path.

**A blocking call with no timeout.** This is less a cause than an amplifier: it converts a transient network blip, a slow container start, or a DNS hiccup into an infinite hang instead of a fast failure. Any HTTP client, socket, or lock acquisition without a deadline is a candidate. Predicts uniformly random hang position, which matches what you see.

**A missed-notification race.** Code that waits for a signal that already fired — a condition variable, a poll loop with a "check then wait" gap, a promise resolved before the listener attached. These are invisible on a fast machine and open up when the runner is throttled. Also predicts uniform random position.

**Pipe buffer deadlock.** A subprocess writes a lot to stdout, nobody drains the pipe, the OS buffer fills (64KB on Linux), the child blocks on write, the parent waits for the child. This is a textbook CI-only hang precisely because locally you have a terminal draining it.

**Cross-run contention on a shared external resource.** If concurrent CI runs share a database, schema, S3 prefix, or namespace, one run can hold a lock the other waits on forever. One in twenty is about the rate at which two runs overlap on a moderately busy repo — check whether hangs correlate with concurrent pipeline runs.

**Cross-test interference under parallelism.** Row locks, a shared fixture, a global registry. Predicts that serial runs never hang.

### The one thing to do before any of this reasoning

Get a stack dump from the hung process. Everything above is a guess until you have one; the dump usually collapses six hypotheses into one in a single look.

Set a job timeout shorter than the platform's kill, and on timeout dump state before dying. Concretely: `jstack` or `kill -QUIT` for the JVM, `kill -QUIT` for Go, `py-spy dump --pid` for Python, `why-is-node-running` or `--detectOpenHandles` for Node. Alongside it, capture `ss -tanp` (socket states and counts), `ls /proc/<pid>/fd | wc -l`, and on the database side `pg_stat_activity` and `pg_locks` or the equivalent. That combination distinguishes "blocked acquiring from the pool" from "blocked reading a socket" from "waiting on a row lock" immediately.

### Cheap discriminating experiments

Run the suite twenty times in a loop in CI with the instrumentation above, rather than waiting for it to happen on its own. Then:

- **Record the hang's position in the run each time.** Late-skewed means cumulative leak; uniform means race or missing timeout.
- **Run with parallelism 1.** If it stops, it's cross-test interference. If it persists, look at external dependencies and leaks.
- **Run only the back half of the suite.** If the hang rate holds constant regardless of which subset you run, nothing is accumulating.
- **Reproduce locally under CI conditions:** the CI container image, `--cpus=0.5`, output redirected to a file rather than a terminal, same parallelism. If it reproduces, you have a debugger.

On the pool theory specifically: check whether your pool is configured with an acquire timeout. If it is, exhaustion produces an *error*, not a hang — and a hang would then rule it out rather than confirm it. If it isn't, set one. That change alone turns a class of silent hangs into a legible stack trace, which is worth doing regardless of what the actual cause turns out to be.