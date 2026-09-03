# Use Postgres `SKIP LOCKED` for background job queueing

## Status

Accepted. Implemented in Q3.

## Context

We are replacing the background job runner we wrote in-house. It has served us to this point, but it lacks durable retries, scheduling, and any visibility into in-flight work, and we do not want to keep extending it. We evaluated three replacements: Celery backed by Redis, RQ backed by Redis, and a queue built on Postgres using `SELECT ... FOR UPDATE SKIP LOCKED`.

Four properties of our situation drove the comparison. The first is volume. We process roughly 30,000 jobs a day and peak around 40 per second, which is one to two orders of magnitude below the load a dedicated broker is designed to absorb. Throughput was therefore not a deciding factor; we are choosing among options that all comfortably clear the bar we actually need to clear.

The second is atomicity, and it turned out to be the decisive one. A large share of our jobs are enqueued inside a database transaction that also writes application state, and the two must succeed or fail together. A job that fires against state its transaction rolled back is a bug, and a committed transaction whose job never arrives is a different bug. A broker running in its own process cannot join a Postgres transaction, so obtaining this property with Celery or RQ means building a transactional outbox: insert the job into a Postgres table inside the caller's transaction, then run a relay process that reads committed rows and publishes them to Redis. The outbox is itself a Postgres queue, and adopting it would leave us operating a Postgres queue *and* a Redis broker to get a guarantee the Postgres queue already provides on its own.

The third is operational surface. We run Postgres today with backups, monitoring, failover, and an on-call rotation that knows how it behaves under stress. Redis would be a second stateful service to provision, patch, monitor, size for memory, and page someone about at three in the morning, and its durability model would need its own decisions about persistence and failover before we could rely on it for work we cannot afford to drop.

The fourth is team experience. Nobody on the team has run Celery in production. Celery's power lives in a wide configuration surface, and so do its failure modes: prefetch counts, `acks_late`, visibility timeouts, result backends, and worker pool types are all places where a misconfiguration produces duplicated or silently lost work under conditions that only appear during an incident. Learning that surface well enough to operate it confidently is a real cost, paid at a time when the queue is new and least understood. RQ is far smaller and would have been much cheaper to learn, but it does not address the atomicity requirement, which left it needing the same outbox as Celery with fewer features in return.

## Decision

We will use Postgres as the queue. Jobs are rows in a `jobs` table; enqueueing is an `INSERT` in the caller's transaction, so a job becomes visible exactly when the writes that justify it commit. Workers claim batches with `SELECT ... FOR UPDATE SKIP LOCKED`, which lets concurrent workers pull disjoint sets of rows without blocking one another or serialising on a single hot lock. We are writing our own retry, backoff, and scheduling logic on top of that primitive rather than adopting a framework.

## Consequences

We accept a throughput ceiling in the low hundreds of jobs per second. Beyond that, polling and row contention make Postgres queueing an unhappy fit, and we would need to move to a purpose-built broker. At 40 per second peak we have roughly an order of magnitude of headroom, which is enough that growth would give us warning rather than an outage, but the ceiling is real and we should treat sustained load above about 150 per second as the signal to revisit this record.

We take on roughly 400 lines of retry, backoff, and scheduling code that Celery would have supplied. This is code we must test, document, and maintain, and it is the part of the system most likely to harbour subtle bugs around clock handling and repeated delivery. The compensating benefit is that the logic is ours, written against our semantics, debuggable with the same tools and the same SQL we use for everything else, and inspectable by anyone on the team without learning a framework first.

Long-running jobs hold a connection from the pool for their duration, which couples job design to database capacity in a way a Redis-backed worker would not. We size the worker pool separately from the web pool so that a backlog of slow jobs cannot starve request handling, and jobs that are expected to run for minutes should be structured to release their claim and checkpoint rather than hold a connection open across the whole run.

Against those costs, we add no new service to the on-call surface, we get exactly-once enqueueing without an outbox, and the queue is queryable: the state of pending, running, and failed work is available to anyone who can write a `SELECT`, with no separate introspection tooling to build or learn.

---

Slot in your ADR number and date when you file it; I left the title unnumbered since I don't know the sequence in your repo. If you want it written to a file in a particular directory and format, say where and I'll add it.