# ADR 0014: Use Postgres `SKIP LOCKED` for Background Job Queueing

**Status:** Accepted. Implemented in Q3.

## Context

Our background work currently runs through a hand-rolled job runner that we have outgrown. It offers no durable retry semantics, no scheduling, and no visibility into what failed or why, and every new job type has required a small amount of bespoke plumbing. We set out to replace it with a real queue and evaluated three options: Celery backed by Redis, RQ, and a queue built directly on Postgres using `SELECT ... FOR UPDATE SKIP LOCKED`.

Four facts about our situation shaped the evaluation. We already run Postgres in production and have operational familiarity with it — backups, failover, monitoring, and the on-call runbooks all exist — whereas Redis would be a new stateful service to provision, secure, monitor, and page someone about at three in the morning; the incremental reliability we would buy from a dedicated broker did not look worth that expansion of the on-call surface. Our volume is also modest, at roughly 30,000 jobs a day with an observed peak around 40 jobs per second, which is two to three orders of magnitude below the point where a database-backed queue becomes the bottleneck. More importantly, most of our jobs are enqueued as a side effect of a database write — an order is created and a confirmation email must follow — and we need the enqueue to commit atomically with that write. A separate broker cannot give us this without an outbox table and a relay process, which means we would end up operating Postgres-backed queueing *and* Redis rather than one or the other. Finally, no one on the team has run Celery in production; its configuration surface, worker model, and failure modes are large enough that the learning would be real, and the operational subtleties tend to surface during incidents rather than during development.

## Decision

We will implement job queueing in Postgres, using a `jobs` table and `SELECT ... FOR UPDATE SKIP LOCKED` to let multiple workers claim disjoint batches without contending on the same rows. Enqueueing is an ordinary `INSERT` inside the caller's existing transaction, so a job becomes visible to workers exactly when the writes that justify it commit, and disappears with them on rollback. Retry, backoff, and scheduling are implemented in application code against columns on the same table.

## Consequences

The gains are the direct inverse of the context above: no new infrastructure, transactional enqueue for free, and a queue our team can reason about with tools we already use — job state is inspectable with `SELECT`, and a stuck queue is debuggable by anyone who can read SQL.

We are accepting three costs knowingly. The approach does not scale past roughly a few hundred jobs per second, since claiming rows means real writes and vacuum pressure on a hot table; at our current volume we have well over an order of magnitude of headroom, but sustained growth toward that ceiling should trigger a revisit of this ADR rather than an attempt to tune past it. We also own about 400 lines of retry and scheduling logic that Celery would have supplied — bounded, testable, and unglamorous code that nonetheless needs maintenance and will grow if our requirements do. And because a worker holds its connection for the duration of a job, long-running work consumes pool capacity that shorter jobs might need; we will run workers with a dedicated pool sized independently of the web tier, and treat any job running longer than a few minutes as a candidate for decomposition or for a different execution path entirely.

## Alternatives considered

**Celery with Redis** is the most capable of the three, with mature scheduling, routing, chords, and a large operational corpus. We rejected it because it adds Redis to the on-call surface, still requires an outbox to get transactional enqueue, and carries a learning curve no one on the team has climbed — three costs paid for throughput we do not need.

**RQ** is considerably simpler than Celery and would have been a reasonable choice on ergonomics alone, but it shares the Redis dependency and the same atomicity gap, which are the two objections that actually decided the question.

## Revisit if

Sustained throughput approaches 200 jobs per second, our home-grown retry and scheduling code starts accreting features that a mature library already provides, or connection-pool contention from long-running jobs becomes a recurring source of incidents.