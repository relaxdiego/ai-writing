# Background jobs run on Postgres `SKIP LOCKED`

**Status:** Accepted. Implemented in Q3.

## Context

Background work currently runs on a job runner we wrote ourselves, and it has reached the point where the failure modes are ours to debug rather than someone else's to document. We want to replace it with a queue that has understood semantics for retries, visibility, and worker crashes.

Our volume is modest and unlikely to change shape soon. We process roughly 30,000 jobs a day, which averages well under one per second, with bursts to about 40 per second. Any of the candidates handles that comfortably, so throughput was not the deciding factor; the deciding factors were operational surface, transactional correctness, and what the team already knows.

The correctness requirement is the sharpest of these. Most of our jobs are enqueued as a consequence of a database write: an order is created and a confirmation job follows, a document is updated and a reindex job follows. If the enqueue and the write are not atomic, we get one of two bugs, either a job that fires for a row that was rolled back or a committed row whose job was never enqueued. A broker that lives outside Postgres cannot give us that atomicity directly. The standard remedy is an outbox table plus a relay process, which means we would be operating both a broker and a Postgres-backed queue-shaped table, and paying for the broker's operational cost without escaping the database-side machinery.

The operational constraint is that we already run Postgres, with backups, monitoring, failover, and on-call familiarity all in place. Adding Redis would add a second stateful system to the on-call surface, with its own persistence configuration, memory limits, and eviction behaviour to reason about at three in the morning. Finally, nobody on the team has run Celery in production, and Celery's configuration surface is large enough that inexperience with it is a real operational risk rather than a matter of reading the docs for an afternoon.

## Decision

We will implement job queueing in Postgres, using `SELECT ... FOR UPDATE SKIP LOCKED` over a jobs table to hand out work to competing workers. Jobs are inserted in the same transaction as the domain writes that cause them, so enqueueing is atomic with the state change it belongs to and no outbox is required. Retry policy, backoff, scheduled execution, and dead-lettering are implemented in our own code on top of that table.

## Alternatives considered

Celery with Redis is the most capable of the three and the one we would reach for at an order of magnitude more volume. We rejected it because it adds Redis to on-call, requires an outbox to meet our atomicity requirement, and asks the team to learn a large framework under production pressure. Its capabilities are real, but they are capabilities for problems we do not currently have.

RQ is considerably simpler than Celery and would have been a smaller thing to learn, but it still requires Redis, so it does not relieve the operational objection, and it still cannot commit a job atomically with the database write that produced it. Choosing it would mean accepting the main cost of the broker approach while getting less than Celery offers in return.

## Consequences

We accept a throughput ceiling of a few hundred jobs per second. That leaves close to an order of magnitude of headroom above our current peak, which is enough for now but is not enough to absorb a change in what we use background jobs for. If a new workload pushes sustained rates into the low hundreds per second, this decision should be reopened rather than tuned.

We take on roughly 400 lines of retry and scheduling logic that a mature queue would have provided. This code is on the critical path for correctness, it needs tests covering worker crashes and duplicate delivery, and it becomes our maintenance burden. The estimate is small enough to be worth paying and large enough that it should not grow casually; substantial additions to it are a signal that we have outgrown the approach.

Long-running jobs hold a connection from the pool for their duration, which couples job execution to a resource that also serves web traffic. We will want workers on a separate pool from the application, and we should treat the pool as a capacity limit to monitor rather than a background detail. Jobs that run for minutes rather than seconds are the ones to watch, and where possible they should be broken into shorter units.

In exchange, we get queue state that is visible to ordinary SQL, backed up with everything else, and recoverable through the same failover path as the rest of our data, with no new system on-call has to learn.