# ADR-0014: Use Postgres `SKIP LOCKED` for background jobs

## Status

Accepted. Implemented in Q3 2026, replacing the hand-rolled runner.

## Context

Our background work currently runs on a job runner we wrote ourselves: a table of pending work, a polling loop, and ad-hoc locking that has produced duplicate execution under concurrent workers more than once. We want to replace it with something whose concurrency semantics we can state precisely.

Three properties drove the evaluation. The first is atomicity with the enqueueing transaction. Most of our jobs are enqueued as part of a database write — send the confirmation email when the booking row commits, reindex the document when the revision lands — and a job that fires for a transaction that later rolled back is worse than a job that never fires at all. A broker outside Postgres cannot give us this directly; it requires a transactional outbox, which is a table, a relay process, and a second at-least-once delivery path to reason about.

The second is operational surface. We run Postgres already, with backups, failover, and on-call runbooks that the team has exercised. Redis would be a new stateful dependency in the paging path, and its failure modes (memory pressure, eviction under `maxmemory`, the durability gap between `AOF` and `RDB`) are ones nobody here has debugged in production.

The third is volume, which is modest and unlikely to change shape soon. We process roughly 30,000 jobs a day, averaging well under one per second, with observed peaks around 40 per second during the morning batch window.

The options compared across the dimensions that mattered:

| | Celery + Redis | RQ + Redis | Postgres `SKIP LOCKED` |
|---|---|---|---|
| New on-call dependency | Redis | Redis | none |
| Atomic with enqueueing txn | only via outbox | only via outbox | yes, natively |
| Practical throughput ceiling | tens of thousands/s | thousands/s | a few hundred/s |
| Retry, scheduling, backoff | built in | partial | we write it |
| Team experience | none | none | Postgres, yes |
| Operational complexity | high | moderate | low |

Celery is the most capable of the three and the least suited to us: its configuration surface, its worker and broker topology, and its failure modes are a body of knowledge we would be acquiring from zero, in exchange for a throughput ceiling three orders of magnitude above our peak. RQ is a much smaller system and was the closer call, but it still puts Redis in the paging path and still leaves the atomicity problem to an outbox.

## Decision

We will implement job queueing in Postgres, claiming work with `SELECT ... FOR UPDATE SKIP LOCKED`.

Workers claim a batch inside a transaction; `SKIP LOCKED` causes concurrent claimants to step over locked rows rather than blocking on them, so N workers pull disjoint batches without coordination:

```sql
WITH claimed AS (
    SELECT id FROM jobs
    WHERE state = 'pending' AND run_after <= now()
    ORDER BY priority DESC, run_after
    LIMIT 10
    FOR UPDATE SKIP LOCKED
)
UPDATE jobs SET state = 'running', claimed_at = now(), claimed_by = $1
FROM claimed WHERE jobs.id = claimed.id
RETURNING jobs.*;
```

Enqueueing is an `INSERT` on the caller's existing transaction, which is the whole point: the job becomes visible to workers exactly when the writes that justify it commit, and disappears with them on rollback.

## Consequences

We accept a throughput ceiling of roughly a few hundred jobs per second. This is a function of write amplification and vacuum load on a high-churn table, not of any tuning we can do; a queue table is the workload Postgres's MVCC design handles least gracefully. At a 40/s peak we have somewhere between five and ten times headroom, which is comfortable but is not the kind of margin that absorbs a change in business model. We should treat sustained load above 150 jobs per second as the signal to revisit this record rather than to tune around it.

We take on roughly 400 lines of retry, backoff, and scheduling logic that Celery would have supplied. This is the cost we are least certain about. The line count is small and the logic is not novel, but it is code we must test against the cases a mature queue has already met: the worker that dies holding a claim, the job that exceeds its visibility timeout while still running, the poison message that fails identically on every attempt. Reaping abandoned claims needs a sweeper that returns rows whose `claimed_at` has aged past a threshold, and getting that threshold wrong in either direction produces either duplicate execution or stuck jobs.

Long-running jobs hold a pooled connection for their duration, since the claim and the work share a transaction. Our pool is sized for request traffic, so a handful of slow jobs can starve it. We mitigate this with a separate pool for workers and a policy that any job expected to run beyond about thirty seconds must checkpoint and re-enqueue rather than hold its transaction open, but the policy is a convention and conventions erode.

Against those costs, the on-call surface does not grow, the atomicity requirement is met without an outbox, and every failure mode of the queue is a failure mode of a database this team already knows how to operate. Debugging a stuck job is a `SELECT`, and the queue is included in the existing backup and point-in-time recovery story at no additional cost.