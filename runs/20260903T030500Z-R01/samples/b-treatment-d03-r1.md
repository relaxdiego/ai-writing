# ADR 0007: Use Postgres `SKIP LOCKED` for background job queueing

**Status:** Accepted. Implemented Q3.

## Context

Our background jobs run on a hand-rolled runner that polls a table with no locking discipline, has no retry semantics, and cannot be scaled beyond a single worker process without duplicate execution. We need to replace it.

Current and near-term load is modest: roughly 30,000 jobs per day, with observed peaks around 40 jobs per second. We already operate Postgres as the system of record and have on-call familiarity with it.

A recurring source of bugs in the existing system is enqueue/write divergence: a job is enqueued for work that the enclosing transaction later rolls back, or a transaction commits but the enqueue is lost. We want enqueueing to be atomic with the database writes that trigger it.

We evaluated three options:

- **Celery with Redis.** Mature, well-documented, broad feature set (scheduling, retries, chords, routing). Requires adding Redis to production and to the on-call surface. No team member has run Celery before. Enqueue is not transactional with Postgres writes; correctness requires a transactional outbox and a relay process.
- **RQ.** Simpler than Celery and easier to reason about, but still Redis-backed, so it carries the same operational addition and the same atomicity gap.
- **Postgres with `SELECT ... FOR UPDATE SKIP LOCKED`.** No new infrastructure. Enqueue is an ordinary insert inside the caller's transaction, so atomicity is free. Retry, scheduling, and visibility logic must be written by us.

## Decision

We will implement job queueing in Postgres using `SELECT ... FOR UPDATE SKIP LOCKED` against a `jobs` table, with worker processes polling for claimable rows.

The decisive factor was atomicity. Enqueueing inside the same transaction as the business write eliminates an entire class of bug that the Redis options can only address by adding an outbox table plus a relay — which is more moving parts than the queue we are writing, and reintroduces Postgres as the durable enqueue path anyway. Given that, adding Redis buys us features we do not currently need at the cost of a second datastore on-call must understand.

Secondary factors: our peak load is two orders of magnitude below where Postgres queueing degrades, and the team's zero Celery experience makes its operational depth a liability rather than an asset during incidents.

## Consequences

**Accepted costs:**

- Postgres-backed queueing does not scale much past a few hundred jobs per second before lock contention and table churn become the bottleneck. We have roughly 10x headroom over current peak. If sustained throughput approaches 200/s we should revisit rather than tune.
- We own approximately 400 lines of retry, backoff, and scheduling logic, including the tests and the on-call knowledge that goes with it. This is code we would otherwise get from a library.
- Long-running jobs hold a connection from the pool for their duration. Pool sizing must account for worker concurrency separately from web concurrency, and jobs that block for minutes will need to be split or moved off this path.

**Follow-ups:**

- Establish a routine `VACUUM`/retention policy for the `jobs` table; completed rows must be pruned or the claim query degrades.
- Add monitoring on queue depth and oldest-unclaimed-job age, since we do not get a broker dashboard.
- Revisit this decision if sustained throughput exceeds ~200 jobs/second, or if we find ourselves reimplementing workflow features (chaining, fan-out/fan-in) that a mature framework already provides.