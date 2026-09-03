# ADR-0014: Background jobs on Postgres `SELECT ... FOR UPDATE SKIP LOCKED`

Status: Accepted. Implemented in Q3 2026, replacing the hand-rolled runner.

## Context

Background work is currently handled by a runner we wrote ourselves: a table of pending work, a polling loop, and advisory locking that we have patched several times to stop double execution. It has no retry policy worth the name, no scheduled execution, and no visibility into why a job failed beyond a log line. We want to replace it with something we can reason about, and the replacement decision is really a decision about what we are willing to operate.

Our volume is modest and well understood. We process roughly 30,000 jobs a day, with an observed peak of about 40 per second during the evening batch window. Nothing in the roadmap suggests an order-of-magnitude change; the largest planned feature adds perhaps 5,000 jobs a day.

The constraint that did the most work in this decision is transactional enqueue. Most of our jobs are created as a side effect of a database write, and a job that runs against a transaction that later rolled back is a correctness bug, not a performance one. We have already shipped two such bugs. Any broker that lives outside Postgres gives us at-least-once delivery of jobs that may reference rows that never committed, and the standard remedy is a transactional outbox: a table in Postgres, a relay process, and a second set of failure modes to operate. If we are going to keep a queue table in Postgres regardless, the case for a second system has to be made on throughput, and our throughput does not make it.

We also weighed the team. Nobody here has run Celery in production. Celery's failure modes (visibility timeouts, prefetch behaviour, result backend growth, worker pool semantics) are learnable, but they are learned during incidents, and we would be learning them at the same time as we learned our own new queue.

## Alternatives considered

Celery with Redis was the most capable option and the one we rejected most deliberately. It gives us retries, scheduling, chains, and a large operational literature for free. It also adds Redis to the on-call surface: another service to provision, monitor, patch, and reason about during a partial outage, with a persistence story we would have to configure correctly to avoid losing enqueued work. Combined with the outbox requirement and zero team experience, the cost lands well above what our volume justifies.

RQ is simpler than Celery and would have been a shorter learning curve, but it does not remove the Redis dependency or the outbox, which are the two costs that actually mattered. It buys us a smaller manual at the same operational price.

Postgres with `SKIP LOCKED` keeps the queue inside the database we already run, back up, monitor, and know how to debug. Enqueue becomes an ordinary insert in the caller's transaction, which makes the atomicity problem disappear rather than mitigating it. Dequeue is a single well-understood statement that locks a batch of rows and skips those held by other workers, and the whole job history is queryable with SQL by anyone on the team.

## Decision

We will implement background job execution as a Postgres table consumed with `SELECT ... FOR UPDATE SKIP LOCKED`. Jobs are enqueued by inserting into that table inside the same transaction as the writes that produce them. Workers claim batches, execute, and record terminal state in the same table.

## Consequences

We accept a throughput ceiling. Row-level locking and per-claim write amplification put practical Postgres queueing somewhere in the low hundreds of jobs per second before contention and vacuum pressure become the dominant concern. At 40 per second peak we have roughly an order of magnitude of headroom, which is enough to be comfortable and not enough to be complacent.

We accept writing and owning retry and scheduling logic, estimated at about 400 lines: exponential backoff with jitter, a maximum attempt count, a dead-letter state, and a `run_after` column for delayed and scheduled work. This is code we will have to test and maintain, and it is code that Celery would have given us. We judged 400 lines of ours easier to debug at 3am than a framework nobody here has read.

We accept that long-running jobs hold a pooled connection for their duration. Worker connections therefore come from a separate pool sized independently of the web pool, so a slow job cannot starve request handling. Jobs expected to run for minutes rather than seconds should be decomposed or moved off this system.

We will revisit the decision if sustained throughput approaches 200 jobs per second, if queue contention shows up in database latency percentiles, or if a use case appears that genuinely needs fan-out or workflow orchestration. At that point the work already done is not wasted: the enqueue interface stays, and the outbox we avoided building becomes the migration path.