# ADR-0014: Use Postgres SKIP LOCKED for background job queueing

## Status

Accepted. Implemented in Q3.

## Context

Our background work currently runs through a hand-rolled runner that polls a table, marks rows in flight with an UPDATE, and relies on a single worker process to avoid double execution. It has no retry policy worth the name, no scheduling, and no way to run more than one worker safely. We need to replace it before the next set of features lands, all of which enqueue work from request handlers.

The workload is modest and we expect it to stay that way for the foreseeable future: roughly 30,000 jobs a day, with observed peaks around 40 per second. Nothing in the roadmap suggests an order-of-magnitude change, and the jobs themselves are ordinary application work rather than a fan-out or ingest pipeline.

The constraint that shaped the decision most is transactional: nearly every job we enqueue is caused by a database write in the same request, and the two must either both happen or neither. A user creates a record and we must send the notification; if the transaction rolls back, the notification must not go out, and if the transaction commits, the job must not be lost. Any broker that lives outside Postgres cannot give us this directly. The standard remedy is the transactional outbox, where the enqueue writes a row inside the application transaction and a relay process forwards it to the broker. That works, but it means we would be operating both a broker and a queue table, and the queue table is most of what we were trying to avoid writing.

Two further facts about our situation are relevant. We already run Postgres in production with backups, monitoring, failover and a team that knows how it behaves under load. And nobody on the team has run Celery before, in production or otherwise.

## Decision

We will implement job queueing in Postgres, using `SELECT ... FOR UPDATE SKIP LOCKED` to hand out jobs to competing workers.

`SKIP LOCKED` gives us the piece that our hand-rolled runner lacked: several workers can poll the same table concurrently, each claiming rows the others have not locked, without contention and without the risk of two workers taking the same job. Enqueueing is an ordinary INSERT, so it participates in the caller's transaction and inherits its atomicity for free. A job that was enqueued by a rolled-back transaction never existed.

## Alternatives considered

Celery with Redis was the obvious industry default and the strongest candidate on features: mature retries, scheduling via Celerybeat, routing, and a large body of operational knowledge to draw on. It loses on two counts here. Redis becomes a second stateful system on the on-call rotation, with its own persistence semantics, failover behaviour and failure modes that the team would be learning during incidents rather than before them. And because the broker sits outside Postgres, atomicity requires the outbox described above. The team's lack of Celery experience compounds both: Celery's failure modes are subtle, and debugging them for the first time under production pressure is a poor trade for features we can approximate in a few hundred lines.

RQ is simpler than Celery and would have been easier to learn, but it still requires Redis and therefore inherits the same two problems without offering enough in return to offset them.

## Consequences

The design has a ceiling. Postgres-backed queueing works comfortably into the low hundreds of jobs per second and degrades past that, as polling and lock contention start to compete with the application's own transactions for the same database. At 40 per second peak we have an order of magnitude of headroom, but this is a decision to revisit rather than a permanent answer. If sustained throughput approaches a few hundred jobs per second, or if a single tenant's fan-out changes the shape of the load, we should reopen this record rather than tune around the edges.

We take on roughly 400 lines of retry and scheduling logic that a mature queue would have given us: backoff policy, attempt counting, dead-lettering, and periodic jobs. This is code we now own, test and maintain, and it will grow somewhat as requirements arrive. We accept it because it is small, ordinary, and entirely within the team's competence, which the alternative was not.

Long-running jobs hold a connection from the pool for their duration. This couples worker concurrency to database connection limits in a way that a Redis-backed system would not, and it means a slow job class can starve the pool. We will run workers against a separate connection pool with its own limit so that job execution cannot exhaust the connections serving web requests, and we will treat job duration as something to monitor rather than something to let drift.