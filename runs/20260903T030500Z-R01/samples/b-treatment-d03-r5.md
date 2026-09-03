# ADR-00X: Use Postgres SKIP LOCKED for background job queueing

**Status:** Accepted. Implemented Q3.

## Context

Our background jobs run on a hand-rolled runner that we have outgrown. We need a real queue with durable job storage, retries, and scheduled execution.

Our constraints:

- We run roughly 30,000 jobs per day, peaking around 40 jobs per second.
- Many jobs are enqueued as part of a database transaction and must not become visible if that transaction rolls back. A job that fires for a row that was never committed is a correctness bug, not a rare edge case.
- We already operate Postgres in production with backups, monitoring, and on-call runbooks. We do not operate Redis.
- Nobody on the team has run Celery before.

We evaluated three options.

**Celery with Redis.** Mature, well documented, handles far more throughput than we need. It adds Redis to the on-call surface — a second datastore to provision, monitor, back up, and page someone about at 3am. Celery's configuration surface is large and its failure modes (lost tasks on broker restart, visibility timeout tuning, prefetch behaviour) take real experience to navigate safely, which we do not have. Transactional enqueue requires an outbox table plus a relay process.

**RQ.** Simpler than Celery and easier to learn, but still Redis-backed, so it carries the same operational cost and the same lack of transactional enqueue.

**Postgres with `SELECT ... FOR UPDATE SKIP LOCKED`.** Jobs live in a table in the database we already run. Workers claim rows with `SKIP LOCKED` so they do not block one another. Enqueue is an ordinary `INSERT` inside the caller's transaction, so a job becomes visible exactly when the writes that justify it commit — no outbox, no relay, no two-phase reasoning.

## Decision

We will use a Postgres table with `SELECT ... FOR UPDATE SKIP LOCKED` as our job queue, and write the retry and scheduling logic ourselves.

The deciding factor was transactional enqueue. Every broker-based option required an outbox to get the guarantee we needed, and an outbox is itself a Postgres-backed queue with a relay process bolted on. Adding Redis to reach a design that still ends with jobs in a Postgres table was not a trade we wanted to make. Our volume is roughly two orders of magnitude below where Postgres queueing gets uncomfortable, so the throughput ceiling costs us nothing today, and the team can debug a table with `SELECT` statements it already knows how to write.

## Consequences

**Accepted costs:**

- *Throughput ceiling.* Postgres queueing degrades somewhere in the low hundreds of jobs per second, driven by lock contention and dead-tuple churn on the queue table. We have roughly 10x headroom over our current peak. If sustained load approaches 200/sec we should revisit rather than tune.
- *Bespoke retry and scheduling code.* About 400 lines we own, test, and maintain — backoff, max attempts, dead-lettering, and delayed execution. This is code that Celery would have given us for free, and it is code that will have bugs.
- *Connection pool pressure.* A running job holds a pooled connection for its duration. Long jobs can starve web request handlers, so job workers must use a separate pool from the application, sized deliberately, and genuinely long-running work should be broken into steps.
- *Table maintenance.* The queue table has high insert/delete churn and needs its own vacuum attention. Neglecting it shows up as slowly degrading claim latency.

**What we gain:**

- No new service in production or on the on-call rotation.
- Atomic enqueue with no outbox.
- Job state is queryable and joinable with application data using existing tools, backups, and point-in-time recovery.

**Revisit if:** sustained throughput approaches 200 jobs/sec, queue-table maintenance becomes a recurring source of incidents, or we need features (complex workflows, fan-out/fan-in, broad scheduling) that push our 400 lines toward reimplementing Celery.