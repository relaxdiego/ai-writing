# ADR 0014: Postgres SKIP LOCKED for background job queueing

**Status:** Accepted. Implemented in Q3.

## Context

Our background work currently runs through a hand-rolled runner that polls a table, marks rows in flight with an update, and relies on a lease timestamp to recover from crashed workers. It has no retry policy worth the name, no scheduling, and no way to observe queue depth other than counting rows by hand. We want to replace it before the next round of feature work adds more asynchronous paths.

The work we need to enqueue is mostly downstream of a database write: a user completes an action, we commit rows, and a job must run as a consequence. Today that coupling is implicit and occasionally wrong, because the runner can pick up a job whose transaction later rolls back. Any replacement has to make enqueue and commit atomic, which for an external broker means an outbox table plus a relay process, so the database is in the critical path regardless of which broker we pick.

Volume is modest and we do not expect an order-of-magnitude change: roughly 30,000 jobs a day, with observed peaks around 40 per second. We already run Postgres with replication, backups, and an on-call rotation that understands it. We do not run Redis anywhere in production, and nobody on the team has operated Celery.

## Decision

We will implement job queueing in Postgres, using `SELECT ... FOR UPDATE SKIP LOCKED` to hand rows to workers. A job is a row in a `jobs` table written inside the same transaction as the business data that causes it, so a rolled-back transaction leaves no job behind and a committed one cannot lose its job. Workers poll with a bounded claim query, process the job, and delete or mark the row in a transaction of their own.

Retry, backoff, and scheduled execution are ours to write. The design is a `run_at` column for scheduling, an `attempts` counter with exponential backoff computed at failure time, and a dead-letter state after a per-job-type maximum. We estimate about 400 lines including the worker loop.

## Alternatives considered

Celery with Redis is the default answer for this problem and brings a mature retry, routing, and scheduling story we would otherwise write ourselves. It fails on two counts here. Adding Redis puts a new stateful service on the on-call surface, with its own persistence semantics and failure modes, to serve a workload our existing database can absorb. And because the broker is separate from the database, atomic enqueue requires an outbox anyway, which means keeping the Postgres machinery and adding Celery on top of it. The absence of Celery experience on the team compounds both problems: the operational subtleties that make Celery worth its complexity at scale are exactly the ones we would be learning during an incident.

RQ is simpler than Celery and would have been the choice if we were adding Redis at all. It does not change the transactional argument, and its scheduling and retry features are not so far ahead of what we need that they justify the new dependency on their own.

## Consequences

Enqueue becomes an ordinary insert, so the atomicity requirement is satisfied by construction and the outbox pattern disappears from the design. Queue inspection is a SQL query, which means existing dashboards, psql sessions, and alerting all work on job state without new tooling. Backup and restore cover the queue along with everything else.

The ceiling is real. Contention on the claim query and the write amplification from row updates put the practical limit in the low hundreds of jobs per second, which is roughly five to ten times our current peak. That is adequate headroom for the volume we can foresee, but it is not a margin that survives a change in what we use jobs for, such as fanning out per-recipient work on a large mailing.

We own the retry and scheduling code, including its bugs. The 400-line estimate covers the happy path and the obvious failure modes; the cost that tends to be underestimated is the long tail of operational affordances, such as requeueing a dead-lettered job, draining a queue for deploy, and rate-limiting a job type that is overwhelming a third-party API. We should expect to add these over time rather than assume the initial implementation is complete.

Long-running jobs hold a pooled connection for their duration, so a slow job type can starve the pool that serves web requests if they share one. Workers will use a separate connection pool sized independently from the application's, and job types expected to run longer than a few seconds should release the claim row's transaction before doing their work, taking the lease-expiry path for crash recovery instead of holding a lock.

We should revisit this decision if sustained throughput approaches 200 jobs per second, if a job type requires fan-out that changes the volume profile by an order of magnitude, or if we adopt Redis for another reason and the marginal operational cost of a broker drops to near zero.