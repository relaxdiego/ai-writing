# ADR-014: Use Postgres `SKIP LOCKED` for background job queueing

## Status

Accepted. Implemented in Q3 2026.

## Context

Background work currently runs on a job runner we wrote ourselves: a table of pending work, a polling loop, and advisory locking bolted on after the first duplicate-execution incident. It has no scheduling, no retry policy worth the name, and no visibility beyond a log line per attempt. Every team that needs deferred work has learned its quirks by breaking it. We want to replace it before it acquires more callers.

Our workload is modest and unlikely to change shape soon. We process roughly 30,000 jobs a day, with observed peaks around 40 per second during the morning import window. The jobs are mostly short: outbound email, thumbnail generation, third-party sync calls. A handful run for minutes rather than seconds.

The requirement that drove the decision is transactional enqueue. Most of our jobs exist because a database write happened, and they are wrong if that write rolls back. A user invitation that is emailed but not recorded, or a sync job for a row that never committed, produces support tickets we have already seen under the current runner. Any broker that lives outside Postgres cannot give us this directly. The standard remedy is a transactional outbox, where the job is written to a Postgres table inside the business transaction and a relay process forwards it to the broker. That works, but it means we operate the broker *and* the outbox, and the outbox is itself a Postgres queue, which is the thing we were trying to avoid writing.

We also weighed operational cost. We run Postgres today with backups, failover, and an on-call rotation that understands it. Redis would be a second stateful system on that rotation, with its own durability configuration, memory-pressure failure modes, and upgrade path. Finally, nobody on the team has run Celery in production. Its configuration surface is large, and its failure modes are learned rather than deduced.

## Decision

We will implement job queueing on Postgres, using `SELECT ... FOR UPDATE SKIP LOCKED` to hand rows to workers without contention. Jobs are rows in a `jobs` table. Producers insert them inside the same transaction as the writes that motivate them, so enqueue is atomic by construction and no outbox is required. Workers poll in a short transaction, claim a batch with `SKIP LOCKED`, and mark terminal state on completion.

We will write the surrounding machinery ourselves: exponential backoff with jitter, a maximum attempt count, a dead-letter state, `run_after` for delayed and scheduled work, and a reaper for jobs whose worker died mid-execution. We estimate this at about 400 lines, and we accept it as code we own and must test.

## Alternatives considered

Celery with Redis was the default expectation and the strongest candidate on features: mature retry semantics, scheduled tasks, chords and chains, and an ecosystem of monitoring tools. We rejected it on the combination of a new on-call system, no team experience, and the outbox we would still have to build to get transactional enqueue. Its scaling headroom is real but irrelevant at 40 jobs per second.

RQ is simpler than Celery and would have been quicker to adopt, but it shares the Redis dependency and the enqueue-atomicity gap while giving up Celery's maturity in exchange. It removed the argument for Celery without removing the reason we did not want either.

## Consequences

The ceiling on this design is a few hundred jobs per second, set by transaction throughput and polling overhead rather than by anything we can tune away. We have roughly an order of magnitude of headroom over current peak, which we judge sufficient for the next few years but not indefinitely.

Retry and scheduling logic is now our code, so its bugs are our bugs and its semantics are undocumented until we document them. We will cover the claim, retry, and reaper paths with tests before the first migration, and treat the module as owned by the platform team rather than shared.

Long-running jobs hold a pooled connection for their duration. At current volumes this is affordable, but it couples job duration to connection-pool sizing in a way that will not be obvious to the next person who writes a ten-minute job. Workers will run on a pool separate from web traffic so that a slow job degrades background work rather than user requests, and we will alert on jobs exceeding a duration threshold.

Queue depth, oldest-pending-job age, and dead-letter count become ordinary Postgres queries, which means our existing dashboards and ad-hoc SQL work on job state without new tooling. That is a genuine gain over an opaque broker, and it partly offsets the monitoring ecosystem we gave up with Celery.

We will revisit this decision if sustained throughput passes 200 jobs per second, if job execution begins to affect primary database latency, or if we find ourselves reimplementing workflow features such as chaining or fan-out joins. Reaching any of those points should trigger a new ADR rather than incremental extension of the queue we are building here.