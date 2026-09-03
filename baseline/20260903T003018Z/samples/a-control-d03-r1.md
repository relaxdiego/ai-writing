No filesystem tools are available in this session, so here is the ADR as text — paste it into `docs/adr/` (or tell me the path and I'll adjust the front matter to match your existing records).

---

# ADR 0007: Use Postgres `SKIP LOCKED` for background job queueing

**Status:** Accepted — implemented Q3 2026
**Date:** 2026-09-03
**Deciders:** Platform team
**Supersedes:** the hand-rolled in-process job runner

## Context

Background work is currently handled by a hand-rolled runner: jobs are held in process, there is no durable retry, and a deploy or crash drops in-flight work. We need a real queue.

Constraints that shaped the decision:

- **Volume is modest.** ~30,000 jobs/day (≈0.35/s average) with an observed peak of ~40 jobs/second.
- **Operational surface matters.** We run Postgres today and are on call for it. Every additional stateful system is a new failure mode, a new backup story, and a new page at 3am.
- **Enqueue must be atomic with the write that caused it.** Most of our jobs are consequences of a database transaction ("user upgraded → send receipt, provision workspace"). If the transaction rolls back, the job must not exist; if it commits, the job must exist. A queue in a separate datastore cannot give us this without a transactional outbox — which means writing the outbox table, the relay process, and its own failure handling, i.e. most of the work we would be trying to avoid.
- **Team experience.** Nobody on the team has run Celery in production. Celery's failure modes (visibility timeouts, lost acks, worker pool semantics, result backend behaviour) are learned expensively.

## Decision

Store jobs in a Postgres table and dequeue with `SELECT ... FOR UPDATE SKIP LOCKED`. Enqueue happens in the same transaction as the business write. Workers poll the table, claim rows with `SKIP LOCKED`, and process them.

We will write our own retry, backoff, and scheduling logic on top of this table (~400 lines).

## Alternatives considered

**Celery + Redis.** The default choice for Python background work, with mature scheduling, retries, and routing already built. Rejected because: it adds Redis to the on-call surface for no capacity we need at 40 jobs/second; the enqueue is not transactional with our database writes, so we would need an outbox anyway; and the team would be learning Celery's operational behaviour during incidents rather than before them. Celery's feature depth is real, but most of it — routing, chords, canvas workflows, multiple brokers — is capacity we would not use.

**RQ.** Materially simpler than Celery and easier to reason about, which addresses the experience concern. Still rejected: it requires Redis (same on-call cost), and still cannot commit a job atomically with the database write that produces it.

**Postgres `SKIP LOCKED`.** Chosen. It is the only option that gives transactional enqueue for free, and the only one that adds no new operational component. The cost is that we build the scheduler ourselves.

The deciding factor was that both Redis options required a transactional outbox to meet our atomicity requirement. Once the outbox is on the table, the "batteries included" advantage of Celery and RQ shrinks considerably — and we would be paying for a second datastore on top of it.

## Consequences

### Accepted costs

- **Throughput ceiling of roughly a few hundred jobs/second.** Polling and row-level lock contention put a practical bound well below what a dedicated broker handles. At a 40/s peak we have roughly an order of magnitude of headroom, but this is the constraint most likely to force a revisit.
- **We own the retry and scheduling logic.** About 400 lines covering claim, backoff, retry limits, dead-lettering, and delayed/scheduled execution. This is code we must test and maintain, and it is code that already exists and is battle-tested in Celery. Bugs here are our bugs.
- **Long-running jobs hold a pool connection for their duration.** A job that runs for minutes occupies a connection the whole time. This couples job concurrency to database connection capacity and means a batch of slow jobs can starve web request handling. Mitigations: a separate connection pool for workers, and a policy that long-running work is chunked rather than run as one long job.
- **Queue load lands on the primary database.** Polling, claims, and job-table writes compete with application traffic, including vacuum pressure from the high-churn job table.

### Benefits

- Enqueue is atomic with the originating transaction — no outbox, no dual-write, no "job fired for a rolled-back change" class of bug.
- No new component on call. Backups, failover, monitoring, and access control are the ones we already have.
- Jobs are inspectable with SQL. Debugging a stuck queue is a `SELECT`, not a Redis CLI session.
- The team can reason about the whole system on day one.

### Operational follow-ups

- Alert on queue depth and oldest-unclaimed-job age.
- Monitor job-table bloat and tune autovacuum for it specifically.
- Run workers against a dedicated connection pool, sized independently of the web pool.

## Revisit if

- Sustained throughput approaches ~200 jobs/second, or peaks exceed it regularly.
- Job-table load becomes a measurable drag on application query latency.
- Connection-pool exhaustion from long-running jobs causes an incident that chunking does not solve.
- We add Redis for another reason (caching, rate limiting), which removes the on-call argument — though not the atomicity one.