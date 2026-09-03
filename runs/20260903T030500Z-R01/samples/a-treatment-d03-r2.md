# ADR: Postgres `SKIP LOCKED` for background jobs

**Status:** Accepted. Implemented in Q3.

## Context

Background work currently runs through a hand-rolled runner we maintain ourselves. We want to replace it with a real queue.

Three requirements shaped the evaluation:

**Transactional enqueue.** Most of our jobs are enqueued as part of a database write — create the record, schedule the work that follows from it. We need those to commit together. If the transaction rolls back, the job must not exist; if it commits, the job must exist. A broker that lives outside Postgres cannot give us this directly. It can be approximated with a transactional outbox, but that means writing the rows to Postgres anyway and then running a relay process to forward them, which is more moving parts than the thing we were trying to avoid.

**Operational surface.** We already run Postgres, and it is already on-call's problem. Adding Redis means a second stateful system with its own failure modes, its own persistence configuration, and its own page at 3am. We did not want to pay that.

**Volume.** About 30,000 jobs a day, peaking around 40 per second. The daily average is well under one job per second; the peak is what matters, and 40/s is not a demanding number.

We evaluated Celery with Redis, RQ, and Postgres-backed queueing with `SELECT ... FOR UPDATE SKIP LOCKED`.

Celery and RQ both fail the transactional-enqueue requirement for the same reason — the queue is not the database — and both add Redis to the on-call surface. Celery brings additional weight of its own: nobody on the team has run it in production, and its configuration surface is large enough that learning it under incident conditions is a real risk. RQ is much simpler than Celery, but simplicity is not what it was competing on; it still fails the first two requirements.

## Decision

We will queue jobs in Postgres, using `SKIP LOCKED` for concurrent dequeue.

Enqueue becomes an ordinary `INSERT` in the same transaction as the business write, which resolves the atomicity requirement completely rather than working around it. Workers poll with `SELECT ... FOR UPDATE SKIP LOCKED LIMIT n`, which lets many workers claim disjoint batches without blocking each other.

## Consequences

**We accept a throughput ceiling of roughly a few hundred jobs per second.** Past that, the polling and row-locking overhead stops being cheap and we would need to move to a real broker. At a 40/s peak this leaves us something like a 5–10x margin. That is comfortable but not unlimited, and a change in workload shape — a new bulk-import feature, a fan-out pattern — could consume it faster than gradual growth would.

**We own our retry and scheduling logic.** Roughly 400 lines: backoff, attempt counting, dead-lettering, delayed execution, and visibility timeouts for workers that die holding a claim. This is code Celery would have given us for free, and it is code we now have to test and maintain. We judged 400 lines of code we understand to be a better trade than a dependency we don't, but the cost is real and it does not go away.

**Long-running jobs hold a connection from the pool** for their full duration, because the claim is a database lock. A handful of slow jobs can therefore squeeze the connections available to serve web traffic. We mitigate this by giving workers a separate pool from the application, but the underlying coupling remains: job duration is now a database resource question, not just a worker resource question.

## Revisit if

- Sustained throughput approaches ~200 jobs/second.
- Job duration or concurrency makes worker pool pressure a recurring incident cause.
- We adopt Redis for another reason, which would change the marginal cost of a broker-based queue.