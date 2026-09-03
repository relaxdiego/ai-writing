# ADR 0007: Use Postgres `SKIP LOCKED` for Background Job Queueing

**Status:** Accepted — implemented Q3
**Date:** 2026-09-03
**Deciders:** Platform team

## Context

Background work is currently handled by a hand-rolled runner: jobs are recorded in an application table and picked up by a polling loop with no locking discipline, no retry policy, and no scheduling primitives. It has been a recurring source of duplicate execution and silently dropped work, and it has no operational visibility. We want to replace it with a real queue before the next round of feature work adds more asynchronous surface area.

Relevant constraints:

- **Volume is modest.** Roughly 30,000 jobs/day, with observed peaks around 40 jobs/second. We have no near-term projection that changes this by an order of magnitude.
- **Transactional enqueue is a hard requirement.** Most of our jobs are enqueued as part of a database transaction that also writes application state (e.g. create order → send confirmation). A job that runs against state that was rolled back, or state that commits without its job, is a correctness bug we have already been bitten by.
- **On-call surface matters.** We operate Postgres today, with backups, monitoring, failover, and people who understand it. Every additional stateful system in the critical path is a new page, a new runbook, and a new upgrade cycle.
- **Team experience.** No one on the team has run Celery in production.

## Decision

We will implement job queueing in Postgres using `SELECT ... FOR UPDATE SKIP LOCKED` against a dedicated `jobs` table, with our own worker loop, retry policy, and scheduler.

Jobs are enqueued with an ordinary `INSERT` inside the caller's transaction. Workers claim batches by selecting ready rows ordered by `run_at`, locking them with `SKIP LOCKED` so concurrent workers do not contend, and marking them in-flight within the same transaction.

## Options Considered

### Celery with Redis

The default answer in our ecosystem. Mature, feature-rich, well-documented; handles retries, scheduling, chaining, and routing out of the box.

Rejected because it adds Redis to the on-call surface, and because Redis is not part of the transaction that enqueues the job. Making enqueue atomic would require a transactional outbox — an outbox table in Postgres plus a relay process pushing to Redis. That is strictly more moving parts than reading the outbox table directly, which is what the chosen option amounts to. Celery's operational complexity (broker semantics, result backends, prefetch and acknowledgement tuning) is also a poor fit for a team with no prior Celery experience.

### RQ

Simpler than Celery and easier to learn, but still Redis-backed, so it carries the same two disqualifiers: a new stateful dependency, and non-transactional enqueue. It buys less than Celery in exchange for the same costs.

### Postgres with `SKIP LOCKED` — chosen

No new infrastructure. Enqueue is a plain `INSERT`, so atomicity with application writes is free rather than engineered. Jobs are inspectable with SQL, which makes debugging and one-off remediation straightforward. The primary cost is that we write the parts Celery would have given us.

## Consequences

### Accepted costs

- **Throughput ceiling.** Postgres-backed queueing degrades somewhere in the low hundreds of jobs/second, driven by row lock contention and table churn. At a 40/second peak we have roughly an order of magnitude of headroom. If sustained load approaches ~200/second we should revisit rather than tune.
- **We own retry and scheduling.** Approximately 400 lines covering exponential backoff with jitter, attempt limits, dead-lettering, and `run_at`-based delayed execution. This is code we must test and maintain, and it will not have Celery's coverage of exotic cases (workflow chaining, complex routing). We accept that we do not currently need those.
- **Long-running jobs hold a pool connection.** A worker executing a job holds its claim transaction open, occupying a connection for the job's duration. Long jobs therefore consume pool capacity that would otherwise serve requests. Mitigation: workers use a dedicated connection pool sized separately from the web pool, and jobs expected to run for minutes should be decomposed or moved off this queue.
- **Table maintenance.** High-churn job tables accumulate dead tuples. We need an aggressive autovacuum setting on the `jobs` table and periodic archival of completed rows.

### Benefits realised

- No new component on the on-call rotation.
- Enqueue is atomic with the writing transaction by construction; the class of bug where a job runs against rolled-back state is eliminated rather than mitigated.
- Queue state is queryable with the tools and access the team already has.
- No new framework for the team to learn.

## Revisit Triggers

We should reopen this decision if any of the following hold:

1. Sustained job throughput exceeds ~200/second, or peaks routinely exceed that.
2. Job-table contention or vacuum pressure becomes a measurable source of latency on primary database traffic.
3. We need workflow features (chains, groups, complex routing) that would materially exceed the ~400 lines we have committed to maintaining.
4. Redis enters our stack for an unrelated reason, removing the on-call argument — though the transactionality argument would still stand and would require an outbox.