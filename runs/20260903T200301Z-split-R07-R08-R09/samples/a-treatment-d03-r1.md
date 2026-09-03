# ADR: Postgres `SKIP LOCKED` for background job queueing

**Status:** Accepted. Implemented in Q3.

## Context

Background work is currently handled by a hand-rolled runner that we want to retire. Any replacement has to fit three facts about our situation. Our volume is modest: roughly 30,000 jobs a day, which averages well under one per second, with observed peaks around 40 per second. Many of our jobs are enqueued as part of a database transaction and are only meaningful if that transaction commits, so an enqueue that survives a rolled-back write is a correctness bug, not a rare annoyance. And we run Postgres today but not Redis, so a broker-based queue means a new service in the on-call rotation, with its own persistence semantics, failover behaviour and upgrade path.

We evaluated three options:

| | New infrastructure | Atomic enqueue with DB writes | Practical throughput | Team familiarity |
|---|---|---|---|---|
| Celery + Redis | Redis, plus Celery's operational model | No, requires an outbox | Tens of thousands/sec | None |
| RQ | Redis | No, requires an outbox | Thousands/sec | None |
| Postgres `SKIP LOCKED` | None | Yes, same transaction | A few hundred/sec | Postgres, yes |

The atomicity column is the one that decided this. A separate broker cannot participate in our database transaction, so getting enqueue-on-commit from Celery or RQ means building a transactional outbox: a table of pending messages, a relay process to drain it into the broker, and the at-least-once delivery and deduplication concerns that come with the relay. Once we are writing and operating an outbox table in Postgres, we are already running a queue in Postgres, and the broker has become a second hop that adds latency and failure modes without removing any of the work. Celery would also have cost us a learning curve on a framework nobody here has operated, at a volume that does not need it.

## Decision

We will implement job queueing in Postgres, using `SELECT ... FOR UPDATE SKIP LOCKED` for workers to claim jobs from a jobs table. Enqueueing is an ordinary `INSERT` inside the caller's transaction, so a job becomes visible to workers exactly when the writes that motivated it commit, and disappears with them if the transaction rolls back.

## Consequences

We keep our operational surface as it is. There is no new service to monitor, back up, secure, upgrade or page anyone about, and the queue inherits Postgres's durability and our existing backup and restore procedure. Job state is queryable with SQL, which means debugging a stuck job is a query rather than a broker introspection tool, and the queue's contents appear in the same snapshot as the data they refer to.

Against that we accept three costs.

- **A throughput ceiling of roughly a few hundred jobs per second.** At a peak of 40 per second this leaves us somewhere between five and ten times headroom, which is comfortable now but is a real ceiling rather than a soft one. Growth in job volume is the specific thing that invalidates this decision.
- **Retry and scheduling logic we own.** Backoff, retry limits, dead-lettering, visibility timeouts for crashed workers, and delayed or scheduled execution are all features Celery would have supplied. We estimate about 400 lines to write and an ongoing maintenance obligation. That code is ours to test and to get right, and bugs in it will look like lost or duplicated jobs.
- **Long-running jobs hold a pool connection.** Each executing job occupies a connection for its duration, so worker concurrency is bounded by the connection pool and competes with request-serving traffic for it. Sizing the pool and capping worker counts becomes a thing we have to reason about, and a burst of slow jobs can starve the application if we get it wrong.

We should revisit this decision if sustained throughput approaches a hundred jobs per second, or if the mix shifts toward long-running jobs that make pool pressure the binding constraint. At that point the outbox that we declined to build becomes the migration path: jobs continue to be written transactionally to Postgres, and a relay drains them to a broker, which is the design we would have been running from the start had we chosen Celery.