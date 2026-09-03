# Use Postgres `SKIP LOCKED` for background job queueing

**Status:** Accepted. Implemented in Q3 2026.

## Context

Background work is currently handled by a job runner we wrote ourselves: jobs are rows in a table, a single process polls them on a timer, and failure handling is whatever each call site remembered to add. It has no retry policy, no scheduling, and no way to run more than one worker safely. We want to replace it with something with real claim semantics before we add more asynchronous work to the product.

Our volume is modest and we expect it to stay that way for the foreseeable roadmap. We process roughly 30,000 jobs a day, with bursts to about 40 per second when a large customer triggers a bulk import. The dominant job types are email sends, webhook deliveries, and report generation, all of which tolerate seconds of latency.

Two constraints shaped the evaluation more than throughput did. The first is atomicity: nearly every job we enqueue is caused by a database write, and enqueueing a job for a transaction that later rolls back has already caused incidents in the current runner. We want the enqueue to be part of the same transaction as the write that justifies it. The second is operational surface. We are a small team with a shared on-call rotation, we already run Postgres with backups, failover, and monitoring that people understand, and adding a second stateful system means adding a second thing to be woken up for.

## Decision

We will use Postgres as the queue, with workers claiming jobs via `SELECT ... FOR UPDATE SKIP LOCKED`. Enqueueing is an `INSERT` in the caller's existing transaction, so a job becomes visible to workers exactly when the writes that caused it commit, and never otherwise. Retry, backoff, and scheduled execution are implemented in application code over columns on the jobs table.

## Alternatives considered

Celery with Redis is the most capable option and the one we rejected most quickly. It gives us retries, scheduling, routing, and a large body of operational knowledge for free, but nobody on the team has run it, its failure modes under broker partition are subtle, and it would put Redis in the on-call rotation. Because Redis is a separate system from our database, enqueueing could not be transactional; we would need an outbox table and a relay process, which means we would be building and operating Postgres-based queueing anyway, underneath a broker we also have to operate.

RQ is the same trade with less machinery. It is markedly simpler than Celery and the team could learn it in an afternoon, but it carries the same Redis dependency and the same lack of transactional enqueue, and its scheduling and retry support is thin enough that we would be writing some of that logic regardless.

Postgres with `SKIP LOCKED` gives up throughput and gives us the two things we actually named as constraints. The claim query is well understood, has been the basis of production queues for a decade, and adds no new component to operate.

## Consequences

We accept a throughput ceiling. Postgres queueing of this shape degrades somewhere in the low hundreds of jobs per second, as claim contention and table churn begin to dominate. Our peak of 40 per second leaves us a factor of several in headroom, which is comfortable but not unlimited; a change in product shape that makes job volume grow with request volume would consume it quickly.

We take on roughly 400 lines of retry and scheduling code that a mature broker would have supplied: attempt counters, exponential backoff with jitter, a `run_after` column for delayed work, a dead-letter state, and the tests for all of it. This is code we now own and must maintain, and it is the most likely place for a subtle bug, particularly around jobs that fail after partial side effects.

Long-running jobs hold a database connection for their duration, because the row lock that constitutes the claim lives inside an open transaction. We will size a separate connection pool for workers so that a backlog of slow jobs cannot starve request-serving traffic, and we will cap job duration, moving anything genuinely long to a chunked design. If holding connections becomes the binding constraint before throughput does, the migration path is a lease column with a visibility timeout and a heartbeat, which trades the connection for a reaper process and weaker at-most-once guarantees.

We should revisit this decision if sustained throughput passes about 150 jobs per second, if queue latency at peak exceeds our tolerance for user-visible work, or if we find ourselves extending the hand-written scheduler toward workflow features such as chains, groups, or fan-out with result collection. Those are the points at which the cost of building exceeds the cost of operating a broker.