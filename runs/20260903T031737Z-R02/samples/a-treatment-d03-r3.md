# Background jobs run on Postgres `SELECT … FOR UPDATE SKIP LOCKED`

**Status:** Accepted — implemented in Q3
**Supersedes:** the hand-rolled background job runner

## Context

The hand-rolled runner has reached the end of its useful life, so we need to choose what replaces it. The workload it has to carry is well understood and modest: roughly 30,000 jobs a day, which averages out below one job per second, with observed peaks around 40 per second. Nothing in the roadmap suggests that number changes by an order of magnitude, and the jobs themselves are ordinary — email sends, webhook deliveries, report generation, index updates.

The constraint that shaped the decision more than volume did is transactional: most jobs are enqueued as part of a database write, and a job that runs against a transaction that later rolled back is a correctness bug, not a nuisance. Any broker living outside Postgres — Redis included — cannot participate in that transaction, so enqueueing to it means either accepting a window where the write and the job disagree, or building an outbox table in Postgres and a relay process that drains it into the broker. The outbox is the standard answer and it works, but it means we would be running a Postgres-backed queue anyway, with a second queue behind it and a relay between them.

Two other facts about the team bear on the choice. We already operate Postgres, with backups, monitoring, failover, and on-call runbooks that people have actually used; adding Redis means adding a second stateful system to that surface, including its persistence and eviction semantics, for a workload that does not need its throughput. And nobody on the team has run Celery in production. Celery is capable and widely deployed, but its configuration surface — result backends, prefetch, acknowledgement timing, broker transport options — is large enough that the failure modes are learned expensively, usually during an incident.

## Alternatives considered

**Celery with Redis** is the most capable option and the one with the deepest ecosystem: scheduling, retries, chords, routing, and rate limiting all come in the box, and we would write none of that logic ourselves. Against that, it brings both new dependencies we were trying to avoid — Redis on the on-call surface and Celery's operational model on a team with no experience of it — and it still does not solve the atomicity problem without an outbox.

**RQ** is much simpler than Celery and would be quicker to learn, but it shares the Redis dependency and offers less scheduling and retry machinery, which narrows the gap between what it gives us and what we would build ourselves. Choosing it means paying the operational cost of a second datastore without getting Celery's feature set in return.

**Postgres with `SKIP LOCKED`** gives us transactional enqueue for free and adds nothing to the on-call surface, at the price of a throughput ceiling and of writing the scheduling and retry logic by hand.

## Decision

We will implement the job queue as a table in our existing Postgres database. Workers claim work with `SELECT … FROM jobs WHERE … ORDER BY run_at FOR UPDATE SKIP LOCKED LIMIT n`, which lets concurrent workers pull disjoint batches without blocking each other or serialising on a single lock. Enqueueing is an `INSERT` in the same transaction as the business write it belongs to, which is the property we bought the whole design for: if the transaction rolls back, the job was never enqueued, and no outbox or reconciliation process is needed to make that true.

Retry policy, backoff, scheduled and delayed execution, dead-lettering, and the visibility timeout for workers that die mid-job are ours to write — roughly 400 lines, based on the prototype. This is the largest thing we are taking on, and we accept it on the grounds that the logic is small, that it is code we can read during an incident, and that a general-purpose queue's version of it would still need configuring and understanding.

## Consequences

The ceiling is real and we should name it plainly. Postgres queueing of this kind runs out of room somewhere in the low hundreds of jobs per second, because every claim is a write to the same hot table and the table competes with application traffic for the same connections, buffers, and vacuum budget. At a peak of 40 per second we have most of an order of magnitude of headroom, which is enough to be comfortable but not enough to ignore. We should treat a sustained peak above roughly 150 jobs per second, or the arrival of a job class that needs more, as the trigger to revisit this record rather than to tune around it — at that point the outbox-plus-broker design becomes the cheaper option, and the transactional enqueue interface we are building now is what makes that migration tractable, since callers keep enqueueing into Postgres and only the drain changes.

Two operational costs follow from the choice. Long-running jobs hold a pooled connection for their duration, so a handful of slow jobs can starve the rest of the system in a way that an external broker would not; we mitigate this with a separate connection pool for workers, sized independently of the web pool, and by treating any job whose expected runtime exceeds a few seconds as something to be split or moved off the main path. The queue table also becomes one of the busiest tables in the database, with a high update-and-delete rate that produces bloat, so it needs its own autovacuum settings and a retention policy that removes completed rows promptly rather than accumulating history nobody queries.

The compensating benefits are worth restating, since they are what we are buying. Jobs are visible to `psql` and to every tool we already point at Postgres, so inspecting the queue, requeueing a batch, or explaining what happened during an incident uses skills the team already has. Backups and point-in-time recovery cover the queue with no additional work, and there is no second system to fail over, monitor, or page anyone about. For a workload of this size, that is a better trade than the throughput we are giving up.