# ADR 0007: Use Postgres `SKIP LOCKED` for Background Job Queueing

**Status:** Accepted — implemented Q3
**Date:** 2026-09-03
**Deciders:** Platform team

---

## Context

Background work is currently handled by a hand-rolled runner: jobs are recorded in an application table and picked up by a polling loop with no locking discipline, no retry policy, and no scheduling support. It has produced duplicate execution under concurrent workers and has no visibility into failures. We want to replace it with something with well-understood semantics.

Constraints that shaped the decision:

- **Operational surface.** We run Postgres today and are on-call for it. Any new stateful dependency adds a component to monitor, back up, patch, and page on.
- **Volume.** Roughly 30,000 jobs/day, peaking around 40 jobs/second. This is two orders of magnitude below what a dedicated broker is built for.
- **Atomicity.** Many jobs are enqueued as part of a database transaction that also writes application state (e.g. "create order, then send confirmation"). If the transaction rolls back, the job must not run. If it commits, the job must run. With a broker outside the database, this requires a transactional outbox — which is itself a Postgres-backed queue plus a relay process.
- **Team experience.** No one on the team has run Celery in production. Its configuration surface (result backends, prefetch, ack semantics, broker-specific failure modes) is a real learning cost.

## Options considered

**Celery with Redis.** Mature, batteries-included: retries, ETA/countdown scheduling, beat, chords, monitoring via Flower. Costs: adds Redis to the on-call surface; Redis as a Celery broker has known durability and visibility-timeout edge cases; no transactional coupling to our Postgres writes without an outbox; substantial operational learning curve for a team with zero Celery experience. The feature set is aimed at a scale and workflow complexity we do not have.

**RQ with Redis.** Much simpler than Celery and quick to learn. Still adds Redis, still cannot enqueue atomically with a database transaction, and its scheduling and retry story is thinner than Celery's — so we would be writing supplementary logic anyway, while also carrying a new datastore.

**Postgres with `SELECT ... FOR UPDATE SKIP LOCKED`.** Workers claim rows from a jobs table under `SKIP LOCKED`, which gives safe concurrent dequeue without contention. Adds no infrastructure. Enqueue is an ordinary `INSERT` inside the caller's transaction, so job creation is atomic with the application writes that motivate it — no outbox, no dual-write window. Retry, backoff, and scheduling must be written by hand.

## Decision

We will implement background job queueing in Postgres using `SELECT ... FOR UPDATE SKIP LOCKED`.

The decisive factor is atomic enqueue. Both broker options require an outbox pattern to give us the transactional guarantee we need — which means building a Postgres-backed queue *and* operating Redis *and* running a relay. Choosing Postgres directly removes two of those three. The volume argument reinforces this: at 40 jobs/second peak we are far inside what a single Postgres instance handles comfortably, so we are not trading away headroom we would actually use. The absence of Celery experience on the team makes the "mature and full-featured" argument weaker in practice than on paper.

## Consequences

### Accepted costs

- **Throughput ceiling.** Postgres queueing degrades somewhere in the low hundreds of jobs per second, driven by row contention, index bloat on the status column, and vacuum pressure from high-churn rows. We are at ~40/second peak, roughly an order of magnitude of headroom. This is a real ceiling, not a soft one — see the review trigger below.
- **We own the retry and scheduling logic.** Approximately 400 lines: attempt counters, exponential backoff with jitter, dead-letter handling, `run_after` scheduling, and stuck-job recovery for workers that die holding a claim. This is code we must test and maintain, and it is where bugs will live.
- **Long-running jobs hold a pool connection.** A job that runs for minutes occupies a connection for its duration. This couples worker concurrency to database connection limits. Mitigation: run job workers against a separate connection pool from web traffic, so a burst of slow jobs cannot starve request handling.

### Benefits

- No new component on the on-call surface; no additional backup, failover, or patching story.
- Enqueue is atomic with the transaction that produces the job. Rollback means the job never existed.
- Job state is queryable with SQL. Debugging, backfills, and ad-hoc "what failed last night" questions need no new tooling.
- Jobs are covered by existing Postgres backup and point-in-time recovery.

### Review trigger

Revisit this decision if sustained throughput exceeds ~150 jobs/second, if job-table churn measurably affects vacuum or replication lag, or if our hand-written retry/scheduling code grows past roughly double its initial size. At that point the migration path is to move the hot job types to a dedicated broker while keeping the Postgres table as the transactional outbox — the atomicity property is preserved and only the delivery mechanism changes.