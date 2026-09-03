# ADR-0014: Use Postgres `SKIP LOCKED` for Background Job Queueing

- **Status:** Accepted — implemented Q3
- **Date:** 2026-09-03
- **Deciders:** Platform team
- **Supersedes:** Hand-rolled background job runner

## Context

Our background work currently runs on a hand-rolled job runner. It has no durable retry semantics, no scheduling, and no visibility, and it has been a recurring source of lost work. We decided to replace it with a real queue.

Constraints that shaped the decision:

- **Volume is modest.** ~30,000 jobs/day, with observed peaks around 40 jobs/second. We are not near any throughput cliff and do not project to be within the planning horizon.
- **Enqueue must be atomic with the writes that cause it.** A large fraction of our jobs are enqueued as part of a database transaction (e.g. "order created → send confirmation"). If the transaction rolls back, the job must not exist; if it commits, the job must exist. With an external broker this requires a transactional outbox — a table, a relay process, and its own failure modes — which is meaningful complexity to own.
- **On-call surface.** We already run and understand Postgres, including backups, failover, and monitoring. Redis would be a new stateful dependency for a small team to learn to operate under pressure.
- **Team experience.** Nobody on the team has run Celery in production. Its configuration surface, worker model, and failure behaviour would be learned during an incident rather than before one.

## Options Considered

### 1. Celery with Redis
Mature, feature-complete: retries, scheduling (beat), routing, chords, result backends. But it adds Redis to the on-call surface, requires an outbox to get transactional enqueue, and carries a large operational and conceptual surface area that no one on the team has experience with. Celery's failure modes (visibility timeouts, prefetch, lost acks on Redis) are subtle and best learned before you need them.

### 2. RQ with Redis
Much simpler than Celery and easier to learn. Still requires Redis, and still cannot give us transactional enqueue without an outbox. Simplicity was not enough to justify the new dependency when the atomicity problem remains unsolved.

### 3. Postgres queueing via `SELECT ... FOR UPDATE SKIP LOCKED`
A `jobs` table polled by workers using `SKIP LOCKED` to claim rows without contention. No new infrastructure. Enqueue is an ordinary `INSERT` inside the caller's transaction, so atomicity is free. Retry, backoff, and scheduling logic must be written by us.

## Decision

**We will use Postgres-backed queueing via `SELECT ... FOR UPDATE SKIP LOCKED`.**

The deciding factor is transactional enqueue. Both broker options solve a throughput problem we do not have while creating a correctness problem we would then have to solve with an outbox. Postgres solves the correctness problem by construction and is comfortably within its performance envelope at our volume. Adding Redis to on-call for a team with no Celery experience is a cost we are not obliged to pay.

## Consequences

### Accepted costs

- **Throughput ceiling of roughly a few hundred jobs/second.** Polling-based Postgres queues degrade under high contention and generate table churn and vacuum pressure. At ~40 jobs/second peak we have roughly an order of magnitude of headroom, but this is a real ceiling and not a soft one.
- **We own our retry and scheduling logic** — approximately 400 lines covering attempt counting, exponential backoff, dead-lettering, and `run_after` scheduling. This is code we must test and maintain, and it will not have the battle-hardening of Celery's equivalent.
- **Long-running jobs hold a pool connection** for their full duration, because the claim is held by a row lock in an open transaction. Long jobs therefore consume connection-pool capacity shared with request-serving traffic.

### Benefits

- No new infrastructure, no new on-call surface.
- Enqueue is atomic with the enclosing transaction; no outbox needed.
- Jobs are queryable with SQL, and are covered by existing backup, replication, and monitoring.
- The whole system is small enough to be read and understood by any engineer on the team.

### Mitigations and follow-ups

- Use a **separate connection pool for workers** so that long-running jobs cannot starve request-serving traffic.
- Set a **maximum job runtime**; jobs exceeding it should be split or moved off the queue path.
- **Alert on queue depth and oldest-unclaimed-job age**, not just on worker health.
- Ensure the claim query is index-backed on `(status, run_after)` and monitor bloat/autovacuum on the `jobs` table.

### Revisit criteria

Reopen this decision if any of the following hold:

- Sustained throughput approaches ~200 jobs/second, or peaks exceed ~500/second.
- Queue-induced load becomes a material fraction of primary database load.
- We need features whose in-house cost exceeds the cost of adopting a broker — fan-out/chords, complex routing, or cross-language workers.

At that point the natural migration is to a dedicated broker plus a transactional outbox, keeping the existing `jobs` table as the outbox — the current design is a strict subset of that end state, so the migration path stays open.