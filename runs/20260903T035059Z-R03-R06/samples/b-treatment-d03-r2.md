# ADR 0014: Postgres `SKIP LOCKED` for background job queueing

**Status:** Accepted; implemented in Q3
**Date:** 2026-09-03

## Context

Our background work currently runs through a hand-rolled runner that polls a table, marks rows in flight with a status column, and relies on a cron-driven sweeper to recover jobs whose workers died. It has no retry policy worth the name, no scheduling beyond "run soon", and its claim mechanism races under concurrent workers, so we run a single worker process and accept the throughput ceiling that imposes. Replacing it is not in question; the decision is what to replace it with.

Three properties of our situation shaped the evaluation. The first is volume: we process roughly 30,000 jobs a day, which averages well under one per second, with observed peaks around 40 per second during bulk imports and the nightly billing run. The second is transactional coupling. Most jobs are enqueued from inside a request that also writes to Postgres, and a job that runs against state its enqueuing transaction rolled back is a class of bug we have already shipped twice. The third is operational: we operate one datastore today, Postgres, and the on-call rotation is four people who have not run Celery in production.

## Decision

We will use Postgres as the queue, with workers claiming jobs via `SELECT ... FOR UPDATE SKIP LOCKED`. Enqueue is an ordinary `INSERT` into a `jobs` table, which means it participates in the caller's transaction and commits atomically with the writes that motivated it. Workers claim a batch inside a transaction, execute, and delete or mark the row on completion; a crashed worker's lock is released when its connection dies, so recovery is a property of the database rather than of a sweeper we have to write and monitor.

We considered Celery with Redis and RQ. Both offer mature retry, scheduling, and result handling that we would otherwise write ourselves, and both scale an order of magnitude beyond anything we project. Neither can give us atomic enqueue, because the broker is a separate system: correctness there requires a transactional outbox, which is a table in Postgres, a relay process, and at-least-once delivery semantics we would have to make our jobs tolerate anyway. Having built most of a Postgres queue to get correctness, we would then also be operating Redis for the part that remains. Redis on the on-call surface means persistence configuration, failover behaviour, memory limits, and a second set of alerts, paid for by four engineers who would be learning it during an incident. Celery carried the additional cost of a large configuration surface the team has no experience tuning; RQ is simpler but shares the broker problem without offering much that we cannot write in a few hundred lines.

## Consequences

We accept a hard throughput ceiling in the low hundreds of jobs per second. Contention on the claim query and index churn on the status column degrade well before Redis would, and our peak of 40 per second leaves roughly a 5x margin rather than the 100x a dedicated broker would give. If sustained throughput approaches 150 per second, or if a single tenant's burst pushes peak past 200, this decision should be reopened rather than tuned.

We take on approximately 400 lines of retry, backoff, and scheduling logic that Celery would have supplied. This is the code most likely to contain subtle bugs, particularly around retry counting under partial failure and around clock handling for delayed jobs, and it needs test coverage proportionate to that risk rather than to its size.

Long-running jobs hold a pooled connection for their duration, which couples worker concurrency to database connection limits in a way our current runner does not expose. Jobs that exceed a few seconds of wall time, especially those blocked on external HTTP calls, will need either a separate pool sized for the worker fleet or decomposition into shorter units. We will set a job timeout and alert on jobs approaching it, since an unbounded job now consumes a resource the web tier also needs.

Queue depth and claim latency become Postgres metrics rather than metrics of a system with its own dashboard, so they need to be added to our existing Postgres monitoring alongside table bloat on the `jobs` table, which will churn heavily and requires an autovacuum setting more aggressive than the default.