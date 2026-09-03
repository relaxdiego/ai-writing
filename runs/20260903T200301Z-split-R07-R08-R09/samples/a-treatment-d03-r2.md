# ADR 0007: Use Postgres `SKIP LOCKED` for background job queueing

**Status:** Accepted. Implemented in Q3.

## Decision

We are replacing the hand-rolled background job runner with a queue built on Postgres, using `SELECT ... FOR UPDATE SKIP LOCKED` to hand jobs to workers. We are not adding Redis or a dedicated broker.

## Context

The existing runner is a set of in-process threads that poll application tables directly, with no shared notion of a job, no retry policy, and no visibility into what failed. It has outgrown the use it was written for, and every new background task pays the cost of reimplementing the same delivery semantics by hand. We want a single queue abstraction with durable jobs, retries, scheduling, and an inspectable backlog.

Three candidates were evaluated against our actual load and our actual operational constraints. Volume is modest: roughly 30,000 jobs a day, which averages well under one per second, with an observed peak around 40 per second. The binding requirement is not throughput but atomicity. Most of our jobs are enqueued as part of a database transaction that also writes application state, and the two must commit or fail together. A separate broker cannot give us that directly; it forces either a transactional outbox with its own relay process, or acceptance of jobs that reference rows that were never committed. We have hit the second failure mode already with the current runner and do not want to design it back in.

The second constraint is the on-call surface. We operate Postgres, we back it up, we know how it fails, and we page on it. Redis would be a new stateful dependency with its own persistence and failover semantics, added for a workload that does not need its speed. The third constraint is experience: nobody on the team has run Celery in production, and its configuration surface is large enough that the learning would happen during incidents.

| | Celery + Redis | RQ | Postgres `SKIP LOCKED` |
|---|---|---|---|
| New infrastructure | Redis | Redis | none |
| Atomic enqueue with app writes | outbox required | outbox required | native |
| Practical throughput | very high | high | a few hundred jobs/s |
| Team familiarity | none | low | high |
| Code we own | little | little | ~400 lines |

Celery and RQ both lose on the two constraints that matter most to us and win on the one that does not. At 40 jobs per second against a ceiling of a few hundred, Postgres leaves us most of an order of magnitude of headroom, and the throughput advantage of a Redis-backed broker buys nothing we can use.

## Consequences

We get transactional enqueue for free. A job row is inserted in the same transaction as the writes that justify it, so a rolled-back transaction takes its jobs with it and a committed one cannot lose them. Jobs are queryable with SQL, which means the backlog, the failure history, and the retry state are all inspectable with tools the team already uses, and they are covered by the existing backup and restore path.

Three costs were accepted deliberately.

- **A throughput ceiling of roughly a few hundred jobs per second.** This is a property of row-level locking and connection contention, not of tuning. Sustained load approaching that figure is the signal to revisit this decision rather than to optimise the implementation.
- **About 400 lines of retry, backoff, and scheduling logic that we own.** Celery and RQ ship this. We are writing and testing it ourselves, including exponential backoff, dead-lettering after a retry ceiling, and a scheduled-for timestamp for delayed work. This code needs the same review and test discipline as application code, because a defect in it silently drops or duplicates work.
- **Long-running jobs hold a pooled connection for their duration.** A worker executing a job occupies a connection that web traffic cannot use. We mitigate this with a separate connection pool for workers, sized independently, so that a slow job class cannot starve request handling. Jobs expected to run for minutes rather than seconds should be split or moved off this queue.

We will revisit this decision if sustained job volume passes roughly 150 per second, if a job class emerges that must run long enough to make connection-holding untenable, or if the retry and scheduling code grows past the point where maintaining it costs more than learning Celery would have.