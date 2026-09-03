No file-writing tools are available in this session, so the record is below; save it as something like `docs/adr/0007-postgres-skip-locked-job-queue.md`.

---

# ADR 0007: Use Postgres SKIP LOCKED for background job queueing

**Status:** Accepted. Implemented in Q3.

## Context

Our background jobs currently run through a hand-rolled runner that we have outgrown, and we need to replace it with something with real queue semantics. The workload is modest: roughly 30,000 jobs a day, with observed peaks around 40 jobs per second. It is not growing in a way that suggests an order-of-magnitude jump in the next few years.

Two constraints shaped the evaluation more than throughput did. The first is transactional: most of our jobs are enqueued as part of a database write, and a job that runs against a transaction that later rolled back is a correctness bug, not a retry. Any broker outside Postgres can only give us this through a transactional outbox, which means a table, a relay process, and the operational care that both need. The second is operational: we already run and monitor Postgres, and adding Redis would put a second stateful system into the on-call rotation, with its own failover behaviour, persistence configuration, and memory-pressure failure modes. The team also has no Celery experience, so the option that looks most standard on paper is the one we would be learning under production load.

## Decision

We will implement job queueing in Postgres, using `SELECT ... FOR UPDATE SKIP LOCKED` against a jobs table to hand work to competing consumers.

Enqueueing is an ordinary insert, so it participates in the caller's transaction and commits atomically with the writes that motivated it. Workers poll a jobs table, claim rows with `SKIP LOCKED` so that concurrent workers do not block one another, and mark completion in the same transaction that does the job's own database work where the job is idempotent by construction.

We considered and rejected two alternatives:

- **Celery with Redis.** The most capable option, and the one with the largest ecosystem, but it costs us a new stateful dependency on-call and requires an outbox to get transactional enqueueing. The team would also be learning both Celery's configuration surface and its failure modes at the same time. At 40 jobs per second, we would be paying for capacity and features we have no use for.
- **RQ.** Lighter than Celery and much easier to learn, but it still requires Redis, so it carries the same on-call and outbox costs without Celery's scheduling and routing to offset them.

## Consequences

The transactional property is the main gain. Enqueue-and-commit is a single database transaction with no relay process, no outbox table, and no window in which a job exists in the broker but not in the database or the reverse. On-call surface is unchanged, and workers reuse the connection pooling, backup, and monitoring we already run.

The costs we are accepting are real and worth stating plainly:

- **Throughput ceiling.** Postgres queueing degrades somewhere around a few hundred jobs per second, mostly through table bloat and vacuum pressure on a high-churn table. Against a 40-per-second peak that is roughly an order of magnitude of headroom, which is enough to be comfortable and not enough to be complacent. If sustained volume approaches 200 per second we should re-open this decision rather than tune our way past it.
- **Retry and scheduling are ours to write.** Approximately 400 lines covering backoff, attempt limits, dead-lettering, and delayed execution. This is code we own, test, and debug, where Celery would have supplied it. The estimate is for the initial implementation; expect it to grow as real failure modes arrive.
- **Long-running jobs hold a pool connection.** A job that runs for minutes occupies a connection for its duration, so worker concurrency is bounded by pool size rather than by CPU. Jobs that are long because they wait on external services should be split or moved off this queue, and we should size the worker pool separately from the web pool so that a slow job backlog cannot starve request handling.

The exit path, if we do outgrow this, is to keep the enqueue API and move its implementation behind a broker with an outbox. Callers writing to a jobs table through a function call do not need to know which one it is, so the migration cost is concentrated in the runner rather than spread across every call site.