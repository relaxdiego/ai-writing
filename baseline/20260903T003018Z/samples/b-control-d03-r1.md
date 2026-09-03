# ADR-00XX: Use Postgres `SKIP LOCKED` for Background Job Queueing

**Status:** Accepted — implemented Q3
**Date:** 2026-09-03
**Deciders:** Platform / backend team

---

## Context

We run background work through a hand-rolled job runner. It has no durable retry semantics, no scheduling, and no visibility into in-flight work; failures are discovered from user reports rather than instrumentation. We want to replace it with a real queue before the next round of feature work adds more asynchronous surface area.

Constraints that shaped the decision:

- **Volume is modest.** Roughly 30,000 jobs/day, with observed peaks around 40 jobs/second. We do not expect an order-of-magnitude increase in the next year.
- **Enqueue must be transactional.** Many jobs are enqueued as part of a database transaction that also writes application state (e.g. create record → send notification). If the transaction rolls back, the job must not run; if it commits, the job must not be lost. An external broker cannot give us this without a transactional outbox and a relay process.
- **On-call surface matters.** We already operate Postgres, including backups, failover, and monitoring. Adding Redis means a second stateful system with its own durability semantics, memory-pressure failure modes, and paging runbook.
- **Team experience.** No one on the team has run Celery in production. Celery's configuration surface (result backends, prefetch, acks-late, visibility timeouts) is a known source of subtle production bugs for teams learning it under load.

## Options considered

**1. Celery with Redis.** The industry-default Python option. Mature, feature-rich: scheduling via Beat, retries, chains and groups, wide operational literature. Costs: adds Redis to the on-call surface; Redis as a broker is not durable by default and needs deliberate persistence configuration to avoid job loss on restart; no transactional enqueue without an outbox; large configuration surface the team would be learning in production. The feature set substantially exceeds what our workload needs.

**2. RQ with Redis.** Much smaller and easier to reason about than Celery, and closer to our actual needs. But it still requires Redis, so it does not avoid the primary operational cost, and it still cannot enqueue transactionally. RQ removes the Celery-complexity objection but not the two objections that mattered most.

**3. Postgres-backed queue using `SELECT ... FOR UPDATE SKIP LOCKED`.** A `jobs` table; workers claim batches with `SKIP LOCKED` so concurrent workers do not contend on the same rows. Enqueue is an ordinary `INSERT` inside the caller's transaction. No new infrastructure. Costs: we implement retry, backoff, and scheduling ourselves; throughput is bounded by Postgres; long-running jobs occupy a pooled connection.

## Decision

We will implement job queueing in Postgres using `SELECT ... FOR UPDATE SKIP LOCKED`.

The deciding factor is transactional enqueue. It is the one requirement that neither broker-based option can satisfy without adding an outbox table plus a relay process — at which point we have built most of a Postgres queue *and* still operate Redis. Given that, the remaining considerations (no new on-call surface, modest volume comfortably inside Postgres' envelope, no Celery experience on the team) all point the same direction.

## Consequences

### Accepted costs

- **Throughput ceiling of roughly a few hundred jobs/second.** Our peak is ~40/s, so we have roughly an order of magnitude of headroom. This is a real ceiling, not a soft one: past it, claim contention and table churn dominate.
- **~400 lines of retry and scheduling logic we own.** Attempt counting, exponential backoff, dead-lettering, and `run_at`-based scheduling are ours to write, test, and maintain. This code is a liability we accepted knowingly; it must be tested as carefully as application code.
- **Long-running jobs hold a pooled connection** for their duration. Worker pool sizing is now coupled to Postgres `max_connections`. Long jobs should be run by a separate worker pool with its own connection budget so they cannot starve short-job throughput.
- **Queue load lands on the primary database.** Job table churn produces dead tuples and competes with application queries for autovacuum attention and I/O.

### Benefits

- Enqueue is atomic with the writing transaction. No outbox, no relay, no dual-write reconciliation, no lost-or-duplicated-job class of bug.
- No new infrastructure: existing backups, failover, monitoring, and access control cover the queue.
- The queue is inspectable with SQL. Debugging a stuck job is a `SELECT`, not a Redis CLI session.
- Job state participates in existing point-in-time recovery.

### Operational follow-ups

- Add a partial index supporting the claim query; monitor its bloat.
- Tune autovacuum on the jobs table more aggressively than the global default.
- Alert on oldest-pending-job age and on dead-letter table growth, not just on worker liveness.
- Run long-running jobs in a separate worker pool with a bounded connection budget.

### Revisit triggers

We should reopen this decision if any of the following hold:

- Sustained throughput exceeds ~200 jobs/second, or peaks approach 500/s.
- Queue load measurably degrades application query latency on the primary.
- We need features whose home-grown cost exceeds the broker's operational cost — workflow chaining, fan-out/fan-in, or cross-language workers.
- Redis enters the stack for another reason, which removes the on-call-surface objection and changes the trade-off.