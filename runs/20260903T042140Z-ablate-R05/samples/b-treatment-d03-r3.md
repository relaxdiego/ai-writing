# ADR 0014: Use Postgres SKIP LOCKED for background job queueing

**Status:** Accepted. Implemented in Q3.

## Context

Our background work currently runs through a job runner we wrote ourselves, which polls a table, has no real retry semantics, and has accumulated enough special cases that nobody wants to change it. We decided to replace it with a proper queue and evaluated three options: Celery backed by Redis, RQ, and a queue built on Postgres using `SELECT ... FOR UPDATE SKIP LOCKED`.

Three facts about our situation shaped the evaluation. The first is operational: we already run Postgres, we already have people who know how to keep it healthy, and adding Redis would mean a second stateful service in the on-call rotation, with its own persistence configuration, failure modes and upgrade path. The second is volume. We process roughly 30,000 jobs a day with a measured peak of about 40 per second, which is nowhere near the level at which the choice of broker starts to matter for throughput. The third, and the one that actually decided it, is transactional. Many of our jobs are enqueued as part of a database write and must not run if that write rolls back, nor be lost if it commits. An external broker cannot give us that directly; getting it requires a transactional outbox, which means a table in Postgres, a relay process, and the deduplication logic that goes with at-least-once delivery. Having built that, we would be operating both the outbox and Redis to get a property that a Postgres-backed queue gives us for free, since the enqueue is just another statement in the same transaction.

Team experience pointed the same way. Nobody here has run Celery in production, and its configuration surface, worker model and failure behaviour are large enough that learning them under incident conditions is a real risk. RQ is considerably simpler, but it still requires Redis and still leaves the atomicity problem unsolved, so its simplicity does not buy back the thing we most needed.

## Decision

We will implement job queueing on Postgres, using `SKIP LOCKED` for concurrent dequeue from a jobs table, with enqueue performed inside the same transaction as the application writes that trigger it.

## Consequences

We accept a throughput ceiling. Postgres queueing degrades somewhere around a few hundred jobs per second, depending on job duration and connection count, which gives us roughly an order of magnitude of headroom over current peak. If sustained volume approaches that ceiling we will need to revisit this decision rather than tune our way past it, and the natural successor is a dedicated broker with an outbox, which is the design we deferred here rather than rejected outright.

We take on code we would otherwise have inherited. Retry with backoff, scheduled and delayed jobs, dead-lettering and visibility timeouts all have to be written and tested by us, an estimated 400 lines. This is genuinely our maintenance burden now, and the mitigation is only that the surface is small and the semantics are ones we control and understand.

Long-running jobs hold a pooled connection for their duration, which couples job execution to a resource the web tier also depends on. We will run background workers against a separate connection pool so that a slow job cannot starve request handling, and we will treat any job that routinely runs for minutes as a candidate for decomposition.

In exchange we get exactly-once enqueue semantics tied to our existing transactions, one stateful service to operate instead of two, and a system the whole team can reason about from the schema.