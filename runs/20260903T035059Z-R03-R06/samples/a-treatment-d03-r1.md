# ADR-0014: Postgres SKIP LOCKED for background jobs

**Status:** Accepted. Implemented in Q3.

## Context

Background work currently runs through a hand-rolled runner: workers poll a table, mark a row in flight with an UPDATE, and pick up anything a crashed worker left stale. It has no scheduling, its retry policy is a fixed three attempts with no backoff, and under concurrency two workers can claim the same row. We want to replace it with a queue we can reason about, and the choice was between Celery on Redis, RQ, and using Postgres itself with `SELECT ... FOR UPDATE SKIP LOCKED`.

Our volume is modest and not on a trajectory that changes its order of magnitude. We process about 30,000 jobs a day, arriving unevenly; the highest burst we have measured is roughly 40 per second, and it comes from a batch import whose arrival rate we control. Throughput was therefore not a deciding constraint, and any of the three options clears our load with room to spare.

What did decide it is atomicity. Most jobs are enqueued in the same request that writes the row the job will operate on, so the enqueue needs to commit with that write or not at all. A separate broker cannot give us this: if the broker accepts and the transaction then rolls back, we have a job for a row that does not exist; if the transaction commits and the broker write fails, the write silently never gets its follow-up. The usual remedy is a transactional outbox, where the enqueue is an INSERT in the caller's transaction and a relay process forwards committed rows to the broker. That remedy is a Postgres queue with an extra hop bolted to its far end, so adopting a broker to avoid writing a queue would leave us writing most of one anyway.

The second consideration is operational surface. We already run Postgres with backups, monitoring, failover, and on-call runbooks that people have used. Redis would be a second stateful system on call, with its own persistence configuration, memory ceiling and eviction behaviour, and its own failover story to learn and rehearse. Related to this, nobody on the team has run Celery in production. Celery's important settings (prefetch, `acks_late`, visibility timeout, the result backend) tend to be learned through incidents rather than from the documentation, and we would be learning them on the system that runs our billing retries.

## Decision

We will use Postgres as the queue. A `jobs` table holds the queue; enqueue is an ordinary INSERT inside the caller's transaction, which gives us the atomicity requirement for free. Workers claim work in a short transaction with `SELECT ... FROM jobs WHERE state = 'ready' AND run_after <= now() ORDER BY run_after FOR UPDATE SKIP LOCKED LIMIT n`, so concurrent workers step past each other's locked rows instead of colliding on them, and a worker that dies mid-job releases its locks when its connection drops.

We will write the retry and scheduling logic ourselves, roughly 400 lines: an attempt counter, exponential backoff with jitter expressed by moving `run_after` forward, a dead-letter state after the attempt limit, and delayed or scheduled jobs as rows inserted with a future `run_after`. This is a small amount of code, but it is code we now own and must test, including the parts that are easy to get subtly wrong, such as the boundary between a job that timed out and a job whose worker was merely slow.

## Alternatives considered

Celery with Redis is the mature option, and its feature set (routing, chords, rate limits, a scheduler) exceeds what we need. It loses on all three of the criteria above: it requires an outbox to enqueue atomically, it puts Redis on call, and the team's first Celery lessons would be learned in production.

RQ is simpler than Celery and small enough to read end to end, which addresses the experience objection. It does not address the other two, since it still needs Redis and still cannot enqueue inside our transaction, and scheduling requires a separate component. Choosing it would mean paying the operational cost of a broker while gaining less than Celery offers in return.

## Consequences

We accept a throughput ceiling in the low hundreds of jobs per second, set by polling and by contention on the queue table. That is roughly an order of magnitude above our measured peak, so it is comfortable now, and it is the constraint most likely to end this decision. Polling also puts continuous load on the primary, and the queue table accumulates dead rows at the rate jobs are completed, so it needs autovacuum tuned more aggressively than a normal table.

We accept ownership of the retry and scheduling code, with the ongoing cost that features Celery would have given us (rate limiting, per-queue routing) become work rather than configuration. We also accept that a running job holds a connection from the pool for its duration, which makes long jobs expensive: workers will use a separate pool from the web tier so that a slow job cannot starve request handling, and their concurrency is capped at that pool's size.

We should revisit this if sustained throughput passes about 150 jobs per second, if p99 claim latency degrades under normal load, or if queue-table vacuuming becomes an operational burden. The migration path from here is to keep the enqueue-as-INSERT interface and turn the jobs table into an outbox relayed to a broker, which preserves the atomicity property that motivated the design.