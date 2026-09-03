# ADR 0000: Use Postgres SKIP LOCKED for background job queueing

**Status:** Accepted — implemented Q3

## Context

Our background jobs run on a hand-rolled runner that we no longer trust to grow with the product. We need a real queue.

Relevant constraints:

- **Volume is modest.** About 30,000 jobs per day, with observed peaks around 40 jobs per second.
- **We already operate Postgres.** Any new stateful service becomes an on-call surface: backups, failover, version upgrades, memory pressure, a new class of 3am page.
- **Jobs must be atomic with the writes that enqueue them.** When a request commits a database change and enqueues follow-up work, either both happen or neither does. A separate broker cannot give us this without a transactional outbox — which is itself a Postgres-backed queue plus a relay process.
- **No Celery experience on the team.** Celery's operational failure modes (prefetch behaviour, visibility timeouts, result backend semantics, worker pool interactions) are learned mostly by being burned by them.

We evaluated three options: Celery with Redis, RQ with Redis, and Postgres-backed queueing using `SELECT ... FOR UPDATE SKIP LOCKED`.

## Decision

We will implement job queueing in Postgres using `SELECT ... FOR UPDATE SKIP LOCKED` against a `jobs` table, with workers polling for claimable rows.

Enqueueing is an ordinary `INSERT` inside the caller's existing transaction, which gives us the atomicity requirement for free and removes the outbox pattern from our roadmap entirely.

## Alternatives considered

**Celery with Redis.** The most capable option and the most machinery. Rejected because it adds Redis to on-call, requires an outbox to satisfy the atomicity requirement, and asks a team with no Celery experience to absorb a large operational surface for throughput we do not need.

**RQ with Redis.** Considerably simpler than Celery and a reasonable fit for our volume. Still rejected: it adds Redis for the same reason, and still requires an outbox. If we were going to run a broker anyway, RQ would be the choice — but the broker is the thing we are declining.

## Consequences

We accept the following costs:

- **A throughput ceiling of a few hundred jobs per second.** This is roughly 5–10x our current peak. Sustained load approaching that ceiling is our signal to revisit, not a surprise failure.
- **We write our own retry and scheduling logic.** Roughly 400 lines: exponential backoff, attempt limits, dead-letter handling, and delayed execution via a `run_after` column. This is code we own and must test, and it is the part of the decision most likely to be underestimated.
- **Long-running jobs hold a pool connection for their duration.** Workers need a separate connection pool from web traffic, and genuinely long jobs need to be chunked or moved off this path.
- **Queue load lands on the primary database.** Job polling, claims, and completions are write traffic on the same instance serving the application. Polling interval and table vacuuming both need attention; the `jobs` table has high churn and will need an aggressive autovacuum setting.

In exchange we add no new service to on-call, we get transactional enqueueing without an outbox, jobs are visible to ordinary SQL for debugging, and the system is small enough that the whole team can read it.

## Revisit if

Sustained throughput approaches 200 jobs per second, job queue traffic measurably degrades application query latency, or we find ourselves rebuilding features (fan-out, chained workflows, rate limiting) that a mature framework already provides.