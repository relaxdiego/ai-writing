# ADR: Use Postgres `SKIP LOCKED` for background job queueing

**Status:** Accepted. Implemented in Q3.

## Context

Background work currently runs through a hand-rolled job runner. We are replacing it with a real queue.

The relevant facts about our workload and team:

- **Volume is modest.** About 30,000 jobs a day — roughly 0.35/s on average, with peaks around 40/s.
- **Enqueue must be atomic with the write that causes it.** Most of our jobs are triggered by a database transaction (a record is created, a job should follow). If the transaction rolls back, the job must not exist; if it commits, the job must exist. A broker that lives outside Postgres cannot give us this directly — it requires an outbox table plus a relay process, which is a second moving part to build and operate.
- **We already run Postgres and do not already run Redis.** Adding Redis means adding it to the on-call surface: persistence configuration, failover behavior, memory limits, another thing to page on at 3am.
- **No one on the team has run Celery in production.**

We evaluated three options.

**Celery with Redis.** The most capable option: mature scheduling, retries, chords, monitoring ecosystem. It costs us a new datastore on-call and a framework nobody here has operated. Celery's failure modes (visibility timeouts, lost acks, worker pool semantics) are learned expensively. It also does not solve the atomicity problem without an outbox.

**RQ.** Simpler than Celery and easier to reason about, but still Redis, so it carries the same operational cost and the same atomicity gap, with less to show for it.

**Postgres with `SELECT ... FOR UPDATE SKIP LOCKED`.** A jobs table, workers polling for unlocked rows. No new infrastructure. `INSERT INTO jobs` participates in the caller's transaction, so atomicity is free rather than engineered. The queue is visible to ordinary SQL, which makes debugging a `SELECT` instead of a specialized tool.

## Decision

We will implement job queueing in Postgres using `SKIP LOCKED`.

The deciding factor is atomic enqueue. Both broker options require us to build an outbox to get the guarantee we need, at which point we are running a Postgres-backed queue *and* Redis. Given that, the operational saving from not adding Redis and the absence of Celery experience on the team both point the same direction, and our volume is nowhere near the point where the choice is forced.

## Consequences

**What we accept:**

- **A throughput ceiling of roughly a few hundred jobs per second.** At a 40/s peak we have something like an order of magnitude of headroom, but it is a real ceiling, and it is the one that will eventually bind.
- **We write our own retry and scheduling logic** — approximately 400 lines covering backoff, retry limits, dead-lettering, and delayed execution. This is code we now own, test, and maintain, and it will be less featureful than Celery's.
- **Long-running jobs hold a connection from the pool** for their full duration. Pool sizing now has to account for job concurrency alongside request concurrency, and a batch of slow jobs can starve web traffic.
- **Queue load lands on the primary database.** Polling, row locking, and job-row churn all consume capacity we were previously spending only on application queries, and the jobs table will need vacuum attention.

**What we get:**

- No new component on-call.
- Enqueue is atomic with the transaction that causes it, with no outbox and no relay.
- The queue is inspectable and repairable with SQL, and jobs are backed up and restored with everything else.
- The team can operate this on day one.

**When to revisit:** sustained throughput approaching low hundreds of jobs per second, job-table load measurably affecting application query latency, or a need for features (complex workflow primitives, fan-out orchestration) that we would otherwise be reimplementing. Any of those is a reason to reopen the broker question — at which point the outbox becomes the migration path rather than an upfront cost.