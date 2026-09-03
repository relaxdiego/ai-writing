# ADR-0007: Use Postgres `SKIP LOCKED` for background job queueing

**Status:** Accepted. Implemented in Q3.

## Context

We are retiring the hand-rolled background job runner and replacing it with a real queue. The candidates we evaluated were Celery backed by Redis, RQ backed by Redis, and a queue table in our existing Postgres database polled with `SELECT ... FOR UPDATE SKIP LOCKED`. Four properties of our situation drove the comparison, and they pointed the same direction.

The first is volume, which is modest and unlikely to change character soon. We process roughly 30,000 jobs a day, an average of well under one per second, with observed peaks around 40 per second. Any of the three options handles that without strain, so throughput did not discriminate between them; what it did do was remove the usual argument for accepting broker complexity, since we are nowhere near the scale at which a dedicated broker earns its keep.

The second is atomicity, and it is the requirement that actually decided the matter. Most of our jobs are enqueued as part of a database transaction that also writes application state, and the two must either both happen or neither. A separate broker cannot give us that. Enqueueing to Redis inside a Postgres transaction produces the familiar dual-write failure: the transaction rolls back and the job runs anyway against state that was never committed, or the broker write fails after the commit and the job is silently lost. The standard remedy is a transactional outbox — a table written in the same transaction and drained into the broker by a relay process — which is itself a Postgres queue, with a broker bolted on downstream. Writing an outbox in order to feed Redis means paying for the Postgres-queue machinery and the broker, and we could not identify what the second half buys us at our volume.

The third is operational surface. We already run Postgres, we already back it up, monitor it, and page on it, and the people carrying the pager already know how it fails. Adding Redis adds a second stateful system to that surface: another thing to provision, another failure mode to learn, another restore procedure to rehearse, and another source of 3 a.m. pages. Redis persistence semantics in particular are a category of incident we have no experience with and would rather not acquire under load.

The fourth is team familiarity. Nobody here has run Celery in production. Celery is a large system with a deep configuration surface and a set of well-documented sharp edges — prefetch behaviour, visibility timeouts, result-backend semantics, worker pool selection — and learning those edges during an incident is expensive. RQ is far simpler and would have cost much less to learn, but it inherits the Redis dependency and the atomicity gap without offering anything that offsets them.

## Decision

We will implement background jobs as a Postgres table consumed with `SELECT ... FOR UPDATE SKIP LOCKED`. Producers enqueue by inserting into that table inside the same transaction as their application writes, which makes enqueueing atomic with the state the job depends on and eliminates the dual-write problem by construction. Workers claim batches by selecting ready rows with `SKIP LOCKED`, so concurrent workers pass over each other's locked rows instead of contending for them, and a worker that dies releases its claims when its transaction aborts. We are writing retry and scheduling logic ourselves rather than adopting a framework.

## Alternatives considered

**Celery with Redis** was rejected on the combination of atomicity and unfamiliarity. It is the most capable option of the three and would comfortably outgrow us, but the capability is aimed at problems we do not have, while its costs — a new stateful dependency, a large operational learning curve, and an outbox to preserve transactional correctness — are all costs we would pay immediately.

**RQ with Redis** was the closer call, since it is small enough to hold in your head and would have cost us little to learn. It still requires Redis on the on-call surface and still cannot enqueue atomically with a Postgres transaction, so it left both of our decisive problems unsolved while saving us only the retry and scheduling code.

## Consequences

We accept a throughput ceiling. Postgres-backed queueing degrades somewhere in the low hundreds of jobs per second, as polling and row churn begin to compete with application traffic for the same database. Against a peak of 40 per second that leaves us most of an order of magnitude of headroom, which is enough for the growth we can currently foresee but not enough to ignore, so throughput belongs on the list of things we watch rather than the list of things we have solved.

We accept owning the retry and scheduling logic, estimated at around 400 lines: backoff, attempt counting, dead-lettering, and delayed execution. This code is ours to test and maintain, and it is code that Celery would have supplied for free. The trade is deliberate — 400 lines we wrote and understand, against a dependency we would be reading the source of during incidents — but it is a real ongoing cost, not a one-off, and the first few edge cases we hit in production will likely add to the total.

We accept that long-running jobs hold a connection for their duration, because the claim is held by an open transaction. Worker concurrency is therefore bounded by connections we are willing to dedicate to it, and a batch of slow jobs can starve web traffic if they share a pool. Giving workers a separate pool, and capping their concurrency explicitly, is follow-on work that should land alongside the first long-running job type rather than after it.

We also take on the maintenance the queue table itself implies. A high-churn table of claimed and completed rows produces dead tuples and index bloat, so the table needs its own autovacuum tuning and a retention policy for finished jobs, neither of which the hand-rolled runner made us think about.

## Revisiting

This decision should be reopened if sustained throughput approaches roughly 150 jobs per second, if queue activity begins to show up as measurable contention or vacuum pressure on the primary, or if we acquire a workload — broad fan-out, cross-service routing, very long-lived jobs — that a queue table serves badly. At that point the atomicity argument still holds, and the likely move is an outbox feeding a real broker rather than a wholesale replacement, which is one reason the enqueue path should stay behind an interface the application code does not see through.