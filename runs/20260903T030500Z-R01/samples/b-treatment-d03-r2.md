# ADR-00X: Use Postgres `SKIP LOCKED` for background job queueing

**Status:** Accepted — implemented Q3

## Context

Our background work runs on a hand-rolled runner that we no longer want to maintain. We need a real queue with retries, scheduling, and visibility.

Constraints that shaped the decision:

- **Operational surface.** We already run Postgres and page on it. Adding Redis means a second stateful system in the on-call rotation, with its own persistence semantics, failover behavior, and memory-pressure failure modes.
- **Volume.** About 30,000 jobs/day, peaking around 40 jobs/second. This is not a high-throughput problem.
- **Transactional enqueue.** Most of our jobs are enqueued as part of a database write and must not exist if that write rolls back. With an external broker this requires a transactional outbox — a table, a relay process, and its own failure modes — which is most of the complexity of a Postgres queue anyway, plus the broker.
- **Team experience.** Nobody on the team has run Celery in production. Celery's failure modes (visibility timeouts, prefetch, result backends, worker pool semantics) are learned expensively.

## Decision

Store jobs in a Postgres table. Workers claim jobs with `SELECT ... FOR UPDATE SKIP LOCKED LIMIT n`, process them, and mark them complete in the same transaction that holds the claim. Enqueueing is an ordinary `INSERT` in the caller's transaction, so jobs commit atomically with the writes that produce them.

We write our own retry, backoff, and scheduling logic — roughly 400 lines.

## Consequences

**Accepted costs:**

- **Throughput ceiling.** Postgres queueing does not scale much past a few hundred jobs/second before lock contention and table churn dominate. That is roughly a 10x headroom over our current peak. If we approach it, this decision must be revisited rather than tuned.
- **Owned code.** Retry policy, backoff, dead-lettering, and scheduled jobs are ours to write, test, and debug. Bugs here are our bugs.
- **Connection pressure.** A worker holds a Postgres connection for the duration of a job. Long-running jobs consume pool capacity that application traffic also needs, so worker pools must be sized against the connection limit, and genuinely long jobs need to be split or moved off this path.
- **Table maintenance.** The jobs table is high-churn and needs deliberate vacuum and archival policy.

**Gains:**

- No new system on-call.
- Enqueue is atomic with application writes; no outbox.
- Job state is queryable with SQL, and backed up and restored with everything else.
- The whole mechanism is understandable by anyone on the team who knows Postgres.

## Alternatives considered

**Celery with Redis.** The most capable option and the one with the most operational headroom. Rejected because it adds Redis to on-call, requires an outbox for transactional enqueue, and no one on the team has run it. Its capacity advantage buys us throughput we do not need.

**RQ.** Simpler than Celery and easier to learn, but still Redis-backed, so it carries the same on-call and atomicity costs without solving the problem Celery's extra capability would at least have justified.

## Revisit when

Sustained throughput approaches ~200 jobs/second, or connection-pool contention from long jobs starts affecting request latency.