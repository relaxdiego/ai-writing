# ADR: Background jobs on Postgres with `SELECT ... FOR UPDATE SKIP LOCKED`

**Status:** Accepted. Implemented in Q3.

## Context

Our background work runs on a hand-rolled runner that we have outgrown. We need something with real semantics for retries, scheduling, and visibility, and we would rather adopt a known pattern than keep extending the one we wrote.

The shape of our workload is modest. We process roughly 30,000 jobs a day, which averages well under one job per second, with observed peaks around 40 per second. Nothing in the current roadmap changes that by more than a small multiple.

The constraint that did the most to decide this was transactional. Most of our jobs are enqueued as a consequence of a database write: a row is created or updated, and a job must run because of it. If the queue lives outside Postgres, the enqueue and the write cannot commit together, and we are left choosing between a job that runs for a write that rolled back and a write that lands with no job behind it. Closing that gap with an external broker means building and operating a transactional outbox, which is a second piece of machinery to get right.

Two operational facts also weighed. We already run Postgres and have the on-call practice to match; Redis would be a new datastore in the paging rotation, with its own failure modes and its own durability questions to answer. And no one on the team has run Celery in production, so its considerable capability comes to us as unfamiliar surface rather than as leverage.

## Decision

We will implement the job queue as a Postgres table, with workers claiming jobs using `SELECT ... FOR UPDATE SKIP LOCKED`. Enqueueing is an ordinary `INSERT` in the same transaction as the business write it belongs to. Retry, backoff, and scheduling logic will be written by us against that table.

## Alternatives considered

Celery with Redis is the option with the most capability and the largest ecosystem, and it is the one we know least. It would add Redis to on-call, and it does not solve the atomicity problem without an outbox, so the transactional work we were trying to avoid remains and the operational surface grows. The capability it offers is aimed at scale we do not have.

RQ is much simpler than Celery and would have been a reasonable choice on complexity grounds. It still requires Redis, and so still carries both the new datastore and the outbox. Having to pay those costs anyway removed the advantage its simplicity would otherwise have given it.

## Consequences

We accept a ceiling. Postgres-backed queueing does not go much past a few hundred jobs per second before contention on the queue table becomes the problem to solve. That is comfortably above our 40 per second peak, but the headroom is a single-digit multiple rather than an order of magnitude, so a step change in volume is a genuine trigger to revisit this, not a distant theoretical one. We should watch sustained peak rate as the signal.

We accept writing and owning about 400 lines of retry and scheduling logic that Celery would have given us. This is code with subtle failure modes around clock handling, visibility timeouts, and poison jobs, and it needs tests to match. It is also code we will understand completely, which is worth something given that no one here understands Celery.

We accept that a running job holds a connection from the pool for its duration. Long jobs therefore consume a scarce resource, and a small number of them can starve the rest of the application. This is the cost most likely to bite first: it argues for keeping job bodies short, for sizing the worker pool separately from the web pool, and for treating any job that routinely runs for minutes as a design problem rather than a tuning problem.

In exchange, we get enqueue and business write in one transaction with no outbox, one datastore instead of two, and a queue our team can reason about on the first day.