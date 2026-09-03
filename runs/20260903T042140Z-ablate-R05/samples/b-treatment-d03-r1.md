# ADR: Postgres SKIP LOCKED for background job queueing

**Status:** Accepted. Implemented in Q3.

## Context

Background work currently runs through a job runner we wrote ourselves. We are replacing it with a real queue, and the choice of queue determines what we operate, what we have to build, and what the failure modes look like when a job goes wrong at 3am.

Three properties of our situation shaped the decision. The first is volume: we process roughly 30,000 jobs a day, with observed peaks around 40 per second. Averaged out that is well under one job per second, so the peak is about two orders of magnitude above the mean and still an order of magnitude below what a single Postgres instance handles comfortably as a queue. The second is transactionality: most of our jobs are enqueued as a consequence of a database write, and the job must not become visible to a worker unless that write commits, nor be lost if it does. Any broker that lives outside Postgres gives us this only through a transactional outbox, which means we would be building and operating a Postgres-backed queue anyway, as a staging area in front of the real one. The third is the team: nobody here has run Celery in production, and the operational knowledge required to debug it under load is knowledge we would be acquiring during incidents rather than before them.

We evaluated Celery with Redis, RQ, and queueing directly in Postgres using `SELECT ... FOR UPDATE SKIP LOCKED`.

## Decision

We will queue jobs in a Postgres table and dequeue with `SKIP LOCKED`. Workers claim rows inside the same database they already talk to, and enqueueing happens in the same transaction as the writes that cause it.

Celery with Redis was rejected on operational cost. It is the most capable option of the three and the one that scales furthest, but adopting it means adding Redis to the on-call surface: another datastore to monitor, another persistence and failover story to understand, another set of behaviours to learn under pressure. Set against a peak of 40 jobs per second, that capability buys us headroom we have no plausible path to needing, at a cost we pay every week. RQ is meaningfully simpler than Celery and would have been a reasonable choice, but it still requires Redis, so it carries the operational cost without removing the atomicity problem. Neither broker can commit a job atomically with the database write that produced it, and once an outbox table enters the design, the argument for the broker in front of it becomes an argument about throughput we do not have.

## Consequences

We accept a throughput ceiling in the low hundreds of jobs per second. Beyond that, contention on the queue table and the write amplification of claiming rows stop being negligible, and the design stops being appropriate. Our peak sits comfortably below this, but the ceiling is real and we should treat sustained load approaching it as a signal to revisit rather than to tune.

We accept that we write our own retry and scheduling logic, estimated at around 400 lines: backoff, attempt counts, dead-lettering, and delayed execution. This is code we own and must test, and it is the part of the decision most likely to be underestimated, since the hard cases are the ones that only appear under partial failure. In exchange it is code we can read, which is not true of the equivalent behaviour inside Celery.

We accept that a running job holds a connection from the pool for its duration, which couples worker concurrency to connection limits and makes long-running jobs disproportionately expensive. We will give workers a separate pool from the request path so that a slow job cannot starve web traffic, and we should treat any job whose runtime is measured in minutes as a candidate for decomposition.

The benefits follow from the same design. There is no second datastore in the deployment, no broker to fail independently of the database, and no window in which a job exists in one system but not the other. Enqueueing is an insert, so it participates in transactions, rolls back with them, and is visible to the same tooling and backups as the rest of our data. Inspecting the queue is a `SELECT`.

## Revisiting

Reopen this decision if sustained throughput approaches a few hundred jobs per second, if connection pressure from long-running jobs starts affecting the request path after pool separation, or if our retry and scheduling code grows past the point where maintaining it costs more than learning Celery would have.