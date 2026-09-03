# ADR: Postgres SKIP LOCKED for background jobs

**Status:** Accepted. Implemented in Q3.

## Context

Background work currently runs through a job runner we wrote ourselves. We want to replace it with something we don't maintain the core of.

Our load is modest: roughly 30,000 jobs a day, peaking around 40 per second.

The constraint that shaped the decision is atomicity. Most of our jobs are enqueued as part of a database transaction that also writes application state — a job is only meaningful if that write commits. With a broker outside Postgres, the enqueue and the commit are two separate operations, and closing the gap means building a transactional outbox: a table of pending messages, a relay process, and the delivery semantics that come with it. That is a second system to operate for a guarantee Postgres gives us directly.

We also have no Celery experience on the team, and adding Redis would put another stateful service on the on-call surface.

We evaluated three options:

- **Celery with Redis.** The most capable and the most operationally expensive. Needs Redis, needs an outbox for atomicity, and needs us to learn Celery's configuration surface before we can debug it at 3am.
- **RQ.** Simpler than Celery, still needs Redis, still needs an outbox.
- **Postgres queueing via `SELECT ... FOR UPDATE SKIP LOCKED`.** No new infrastructure, atomic enqueue for free, but the least functionality out of the box.

## Decision

We will queue jobs in Postgres, with workers claiming rows using `SELECT ... FOR UPDATE SKIP LOCKED`.

Enqueueing is an `INSERT` in the same transaction as the business write, so a job exists if and only if the state that justifies it exists.

## Consequences

**What we accept:**

Postgres queueing does not scale past roughly a few hundred jobs per second. At 40/sec peak we have about an order of magnitude of headroom, which is enough for now but is a real ceiling. If sustained throughput approaches that range, this decision should be revisited rather than tuned.

We write our own retry and scheduling logic — backoff, retry limits, dead-lettering, delayed execution. We estimate about 400 lines. This is code we own and must test, and it is the part of the decision most likely to be underestimated.

Long-running jobs hold a connection from the pool for their duration. Job concurrency is therefore bounded by connection capacity, and a slow job class can starve the application of connections. Long jobs need their own pool, or a design that checkpoints rather than holding the transaction open.

**What we get:**

No new service in the on-call rotation. Jobs are visible to `psql`, backed up with everything else, and inspected with SQL. Enqueue is atomic with the writes it depends on, with no outbox.

**Revisit if:** sustained throughput approaches a few hundred jobs per second, or our retry and scheduling code grows past the point where maintaining it costs more than learning Celery would have.