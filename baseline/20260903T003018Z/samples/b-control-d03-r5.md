# ADR-00XX: Use Postgres `SKIP LOCKED` for Background Job Queueing

**Status:** Accepted — implemented Q3 2026
**Deciders:** Platform / backend team
**Supersedes:** the hand-rolled in-process job runner

## Context

Our background work currently runs on a hand-rolled runner that we want to retire. We need a real queue with durable job storage, at-least-once delivery, retries, and delayed/scheduled execution.

Relevant facts about our situation:

- **Volume is modest.** ~30,000 jobs/day, which is ~0.35 jobs/sec on average, with observed bursts to ~40 jobs/sec. Peak is roughly 100x average, so the workload is bursty but small in absolute terms.
- **We already operate Postgres.** It is in our backup, monitoring, failover, and on-call runbooks. Redis is not. Adding it means a new datastore to provision, patch, monitor, capacity-plan, and page someone about at 3am.
- **Transactional enqueue is a hard requirement.** Many of our jobs are enqueued as part of a database transaction that also writes application state (create user → send welcome email; record payment → issue receipt). If the enqueue and the write are not atomic, we get either phantom jobs referencing rows that were rolled back, or lost jobs for writes that committed. An external broker cannot give us this without a transactional outbox — which means storing jobs in Postgres anyway, plus a relay process, plus the broker. That is strictly more machinery than storing jobs in Postgres and reading them from Postgres.
- **No Celery experience on the team.** Celery is powerful but has substantial operational surface area (prefetch semantics, result backends, worker pool models, visibility timeouts, well-known failure modes around late acks and lost tasks). Nobody here has debugged it under load.

## Decision

We will implement job queueing in Postgres, using `SELECT ... FOR UPDATE SKIP LOCKED` to hand out jobs to competing workers.

The design in brief:

- A `jobs` table holds queued work: payload, queue name, `run_at`, `attempts`, `state`, and locking metadata.
- Workers poll with `SELECT ... FROM jobs WHERE state = 'ready' AND run_at <= now() ORDER BY run_at FOR UPDATE SKIP LOCKED LIMIT n`, which lets concurrent workers claim disjoint job sets without blocking each other.
- Enqueue is a plain `INSERT` inside the caller's existing transaction. Atomicity is free: if the transaction rolls back, the job never existed.
- Retries, backoff, scheduling, and dead-lettering are implemented in application code (~400 lines).
- Completion deletes (or archives) the row in the same transaction that commits the job's side effects where possible.

## Consequences

### What we get

- **No new on-call surface.** One datastore. Existing backups cover the queue. Existing monitoring covers queue depth (it's just a `COUNT`). Existing failover story applies.
- **Atomic enqueue, no outbox.** The requirement that drove this decision is satisfied by construction, with no relay process and no dual-write reconciliation.
- **The queue is inspectable with SQL.** "What's stuck?", "what failed last night?", "why is this job retrying?" are all `SELECT`s. Debugging uses tools everyone already knows.
- **Low conceptual cost.** The team can read the entire implementation in an afternoon.

### What we accepted

- **A throughput ceiling of roughly a few hundred jobs/sec.** Beyond that, row contention, index churn, and dead-tuple/vacuum pressure from high-turnover writes make this design a bad fit. At a 40/sec peak we have roughly 5–10x headroom. This is adequate but not enormous, and it is the primary thing to watch.
- **We own retry and scheduling logic.** ~400 lines of code that Celery or RQ would have provided. This is code we must test, maintain, and get right — particularly backoff, attempt counting, and the crash-recovery path that reclaims jobs whose worker died mid-execution.
- **Long-running jobs hold a pooled connection.** A worker executing a 10-minute job occupies a connection for 10 minutes. This constrains worker concurrency against `max_connections` and makes long jobs a capacity concern in a way they would not be with an external broker. Mitigations: a dedicated worker connection pool sized separately from the web pool, and a policy that jobs over ~1 minute should checkpoint or be decomposed.
- **Table maintenance is now our problem.** A high-churn `jobs` table needs deliberate vacuum settings and a retention/archival policy for completed and dead-lettered rows.

## Alternatives considered

**Celery with Redis.** The most capable option: mature scheduling, routing, chords/groups, a large ecosystem. Rejected because it requires adding Redis to the on-call surface, it still cannot give us transactional enqueue without an outbox (so it does not remove the Postgres dependency it was meant to justify), and no one on the team has operated it. The feature surface far exceeds what 30k jobs/day requires; we would be paying operational complexity for capability we would not use.

**RQ.** Meaningfully simpler than Celery and a decent fit for our volume. Still rejected: same Redis on-call cost, same lack of transactional enqueue, and Redis's default persistence characteristics make durability of queued jobs a configuration question rather than a given. Given we would need Postgres in the loop anyway for atomicity, RQ ends up as an additional moving part rather than a replacement for one.

**Postgres `SKIP LOCKED` (chosen).** Weakest on raw throughput, strongest on the two axes that actually bind us: operational surface and transactional enqueue.

## Revisit triggers

This decision should be reopened if any of the following hold:

1. Sustained throughput exceeds ~150 jobs/sec, or peaks routinely exceed ~300/sec.
2. Queue-related load becomes a material fraction of primary database CPU or I/O, or vacuum pressure on `jobs` starts affecting unrelated queries.
3. We need features that would substantially grow the 400 lines — complex workflow orchestration (fan-out/fan-in, chained dependencies), or per-tenant fair scheduling.
4. Redis arrives in our stack for an independent reason, removing the on-call argument. Note that even then, transactional enqueue would still require an outbox, so this alone is not sufficient to switch.

If we do outgrow this, the migration path is reasonable: the `jobs` table becomes the outbox, a relay publishes to the broker, and job handler code is largely unchanged.