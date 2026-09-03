Your skepticism is well founded, though not because pool exhaustion is impossible — because as stated it doesn't explain the symptom you actually have. A pool that runs out of connections normally *fails* rather than hangs: HikariCP's `connectionTimeout` and SQLAlchemy's `pool_timeout` both default to 30 seconds, and you'd get a loud "timed out acquiring connection" naming the test that couldn't get one. Exhaustion from a slow leak also drifts: each test leaks a connection, so the wall gets hit at a roughly fixed count, and the failure clusters in the same region of the run rather than landing uniformly anywhere. The variant that *would* fit your symptoms is different — a pool handing out a connection whose underlying socket is dead, so the client blocks forever in `recv` on a peer that will never answer. Worth separating those two, since they have different fixes and different fingerprints.

The two facts doing the most work here are that the failing test moves around and that it never reproduces locally. Together they say the bug isn't in any test's logic; it's in shared state that accumulates across tests, or in an environmental property of the runner that your laptop doesn't have. Before ranking causes, check one cheap thing that splits the space in half: does the suite print its summary line before it hangs? A surprising fraction of "CI hangs" are the process failing to *exit* after all tests pass — a non-daemon thread, an unjoined child, an unclosed event loop — and the "test it hung on" is just the last one that logged. Different bug class entirely, and free to rule out.

## The realistic candidates

**Left-open transaction, next test blocks on the lock.** A test fails or exits early without rolling back, leaving a session `idle in transaction` holding a row or table lock. Whatever test runs next and touches that row waits — and Postgres `lock_timeout` defaults to `0`, meaning wait forever. Which test hangs depends entirely on ordering, so it moves.

**A child process died and nobody noticed.** The runner hits its cgroup memory limit, the OOM killer takes the database container or a stub server rather than the test process, and the test blocks on a socket to a corpse. Uniformly random in position because it depends on which test was in flight when memory peaked.

**An I/O call with no timeout.** Any `requests.get` without `timeout=`, any bare `socket.recv`, any `subprocess.communicate()` without a deadline. Locally these return in a millisecond so the missing timeout is invisible; on a CI network with real packet loss between containers, one dropped SYN and you're waiting on a black hole.

**Service-container readiness that's checked by port, not by query.** Postgres opens its socket before it's ready to serve, and a client that retries forever will do exactly that. These hangs cluster near the start of a run, which is a testable signature.

**Thread pool or event loop deadlock** — the real analog of the pool theory. All workers blocked on a future whose resolution needs a worker. Deterministic once you're in it, and it looks exactly like exhaustion.

**Pipe buffer.** A subprocess writes past 64 KB to a stdout nobody is draining, blocks on `write`, while the parent blocks on `wait`. Only manifests when the child is chatty, which in CI often means a retry loop that never fires locally.

## Make it produce evidence

The highest-value change is converting silence into a stack trace, because one hang with a dump beats any amount of ranking. Add a per-test timeout that dumps rather than just kills — for Python, `pytest --timeout=60 --timeout-method=thread`, or `faulthandler.dump_traceback_later(60, exit=False)`; for the JVM, `jstack` on SIGQUIT; for Go, `SIGQUIT` gives you every goroutine. Wrap the whole invocation so that on timeout it also captures `ss -tanp`, `ps -eLf`, `cat /sys/fs/cgroup/memory.events`, and on the database side `SELECT * FROM pg_stat_activity` plus `pg_locks`. That bundle distinguishes nearly every hypothesis below in a single occurrence, and it stops you burning an hour of CI on each hang.

| Hypothesis | Distinguishing evidence |
|---|---|
| Pool exhaustion | `ss` shows exactly `pool_max` connections to the DB; hang position drifts later in the run; setting `pool_timeout=10` converts hang → named error |
| Stale connection in pool | Stack in `recv`; socket ESTABLISHED with a peer that restarted; fixed by `pool_pre_ping` / `maxLifetime` |
| Lock wait | `pg_stat_activity` shows `idle in transaction`; hanging test is always *adjacent* to one particular test; `lock_timeout` converts hang → error |
| OOM-killed sibling | cgroup `oom_kill` counter nonzero; `dmesg` confirms; raising runner memory changes the rate |
| Missing timeout | Stack lands in a blocking read/connect; adding timeouts converts hang → flaky failure |
| Readiness race | Hangs cluster in the first minute; a real-query probe eliminates them |
| Thread/loop deadlock | Dump shows all pool threads parked on futures |
| Pipe buffer | Stack shows `wait`/`communicate`; child log volume near a 64 KB multiple |

## Closing the local gap

"Never locally" is almost always a difference of degree. Run the CI image under the runner's actual limits (`docker run --cpus=2 --memory=4g`) rather than on a laptop with ten times the CPU and no memory cap, and add network impairment to the service link with `tc qdisc add dev lo root netem delay 50ms 20ms loss 0.5%` — that one trick shakes out missing timeouts better than anything else, because inter-container CI networks lose packets in ways loopback never does. Then loop the suite a hundred times overnight; at one in twenty you should see about five hangs, which is enough signal to confirm a fix rather than declare victory on a quiet week.

One more thing worth checking early, since it's a single grep: is test order randomized in CI? If it is, ordering-dependent causes are fully consistent with a moving failure point and you can replay the exact order from the seed in the logs. If it *isn't* randomized and the failure still moves, ordering-dependent leaks drop sharply in likelihood and the timing- and environment-driven causes rise.