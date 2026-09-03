Your skepticism is reasonable, and the "always at a different test" detail is doing more work than it might appear.

## What the evidence already narrows

A hang that lands somewhere different each run argues against any single test being buggy, and points instead at either a shared resource that degrades over the course of the run or an environmental condition that can strike at any moment. Those two families have different fingerprints, which is what you can exploit to tell them apart without guessing.

Pool exhaustion isn't a silly hypothesis — it would explain both "integration tests only" and "never locally," since local runs typically hit a database with a fresh process and no contention. But it has a specific problem as an explanation for a *hang*: essentially every real pool has a finite checkout timeout. SQLAlchemy's `pool_timeout` defaults to 30 seconds and raises, HikariCP's `connectionTimeout` defaults to 30 seconds and throws. If the pool were genuinely running dry you would expect a loud exception at a consistent point, not silence. So the hypothesis only survives if someone explicitly configured an infinite wait, and checking that config takes about two minutes. Worth doing first, because it either kills the theory or promotes it sharply.

The mechanisms I'd actually weight higher, given the symptoms:

**A socket read with no timeout.** A connection to Postgres, Redis, a broker, or a mocked external service gets silently dropped — NAT idle timeout on a cloud runner, a container network hiccup, a peer that vanished without sending FIN — and the client blocks forever because no read deadline was ever set and TCP keepalive is off by default. This produces exactly your symptom: uniform in position, rare, and invisible locally where the network is a loopback that never misbehaves.

**A subprocess pipe deadlock.** If any test spawns a child process with `stdout=PIPE` and then waits on it without draining, the child blocks once it has written 64 KiB into the pipe buffer, and the parent waits on a child that will never exit. This is a classic CI-only hang because verbosity, logging config, and terminal-vs-pipe behaviour all differ from your local run.

**A concurrency bug that only interleaves badly under CPU starvation.** CI runners commonly have two cores against your eight or sixteen, and anything sizing a worker pool from `cpu_count()` behaves differently there. Lock-ordering races, an async task awaiting something that needs the loop it's blocking, a `join()` on a thread that's waiting on a queue nobody will fill — all of these need an unlucky schedule, and a starved two-core box produces unlucky schedules far more often.

**A dependency service dying mid-run.** A Postgres or Kafka container that gets OOM-killed leaves everything downstream blocking on connect. Check the runner's memory ceiling and the container exit codes; the kernel will have logged the kill.

**Randomized test ordering plus shared state.** If you're running something like `pytest-randomly`, "a different test each time" may just be ordering, and the real bug could be a specific *pair* of tests that deadlock when adjacent. The seed is printed at the top of the run, so this is cheap to check and cheap to replay.

## How to discriminate

Stop reasoning about it and get a stack dump from the hung process — that single step collapses most of the list above immediately. The critical detail is that your CI job timeout must be *longer* than your in-process watchdog, otherwise the runner tears down the container and you lose the evidence you came for. In Python:

```python
# conftest.py
import faulthandler, os
faulthandler.enable()
faulthandler.dump_traceback_later(int(os.environ.get("HANG_TIMEOUT", "600")), exit=True)
```

Better still, add `pytest-timeout` with `--timeout=60 --timeout-method=thread`, which dumps every thread's stack before killing the run, so you get per-test granularity rather than one whole-suite snapshot. On the JVM, send `SIGQUIT` for a thread dump; in Go, `SIGABRT` gives you every goroutine; in Node, `kill -USR1` plus the inspector, or `--stack-trace-limit` with a watchdog timer. Whatever the runtime, the stack tells you directly whether you're parked in a socket read, a pool acquire, a lock, or `waitpid`.

While you're waiting for a hang to reproduce, collect the cheap signal too. Log each test's start with a timestamp and an ordinal, flushed immediately, and record file-descriptor and connection counts as you go:

```python
@pytest.fixture(autouse=True)
def _resource_watch(request):
    n = len(os.listdir("/proc/self/fd"))
    print(f"START {request.node.nodeid} fds={n}", flush=True)
    yield
```

Across a dozen runs, plot where the hang lands as a fraction of the way through the suite. A leak or accumulating exhaustion skews the distribution late, because it takes N tests of leaking before the resource runs out, and the fd count will climb monotonically to match. An environmental or race-driven hang spreads uniformly and leaves the fd count flat. That histogram alone separates the pool-exhaustion family from everything else, and it costs you nothing but re-runs you're already paying for.

To force reproduction rather than waiting on a 1-in-20 lottery, run the suite locally under CI-like constraints — `docker run --cpus=1 --memory=2g` in a loop — which reproduces a surprising fraction of CI-only concurrency bugs within a few iterations. If you suspect the no-timeout socket theory specifically, confirm it directly by blackholing the database port mid-run with `iptables -A OUTPUT -p tcp --dport 5432 -j DROP` and watching whether the suite hangs forever or fails promptly; a suite that hangs has told you it has no read deadlines regardless of what triggered the original incident.

## Worth doing regardless

Set explicit timeouts at every layer — socket read, HTTP client, pool checkout, and a per-test ceiling — because doing so converts every one of these hangs into a failure with a stack trace attached. It doesn't fix the underlying bug, but it turns an opaque 1-in-20 stall into a diagnosable error, and it means the next occurrence hands you the answer instead of another round of speculation.