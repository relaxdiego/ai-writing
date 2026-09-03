# ADR-00X: Use Postgres SKIP LOCKED for Background Job Queueing

**Status:** Accepted — implemented Q3
**Date:** 2026-09-03

## Context

Our background work runs on a hand-rolled job runner that we no longer want to maintain. We evaluated three replacements: Celery with a Redis broker, RQ, and a queue built on Postgres using `SELECT ... FOR UPDATE SKIP LOCKED`.

The relevant facts about our situation:

- We already operate Postgres and have on-call familiarity with it. Redis would be a new component in the on-call surface, with its own failure modes, persistence configuration, and upgrade path.
- Job volume is modest: roughly 30,000 jobs per day, peaking around 40 per second.
- A significant fraction of our jobs are enqueued as part of a database transaction and must not run if that transaction rolls back — nor be lost if it commits. With a separate broker this requires a transactional outbox and a relay process; with a queue table it is a plain `INSERT`.
- Nobody on the team has run Celery in production. Its configuration surface, worker model, and failure semantics would be new to all of us.

## Decision

We will implement job queueing as a Postgres table consumed with `SELECT ... FOR UPDATE SKIP LOCKED`. Enqueue is an `INSERT` in the caller's transaction. Workers poll a batch, lock rows with `SKIP LOCKED`, execute, and mark terminal state in a follow-up transaction.

## Consequences

**What we get.** No new infrastructure and no new on-call surface. Atomic enqueue with the writes that trigger it, with no outbox machinery and no window where the database and the queue disagree. Jobs are inspectable and repairable with SQL, which the whole team already knows. Our peak load is roughly an order of magnitude below where this approach strains.

**What we accepted.**

- *Throughput ceiling.* Postgres queueing degrades somewhere in the low hundreds of jobs per second, largely from row churn and vacuum pressure on the queue table. That is about 5–10x our current peak. If sustained throughput approaches that range, we revisit this decision rather than tune around it.
- *Retry and scheduling are ours to write.* Roughly 400 lines covering attempt counts, backoff, visibility timeouts for crashed workers, and delayed execution. This is code we own and must test; Celery would have supplied it.
- *Long jobs hold a pool connection.* A worker executing a job occupies a connection for the job's duration. Long-running jobs therefore constrain worker concurrency against the pool, and we size the pool accordingly. Jobs expected to run for minutes should either be split or moved off this queue.

## Revisit if

Sustained throughput passes ~150 jobs per second, queue-table maintenance becomes an operational burden, or we find ourselves reimplementing enough of a broker's feature set (fan-out, priorities across many queues, complex routing) that adopting one becomes cheaper than continuing.