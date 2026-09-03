# ADR 0014: Use Postgres `SKIP LOCKED` for Background Job Queueing

**Status:** Accepted — implemented Q3
**Date:** 2026-09-03
**Supersedes:** the hand-rolled background job runner

## Context

Our background work currently runs through a job runner we wrote ourselves, which has accumulated the usual defects of that genre: no durable retry semantics, no visibility into what is queued, and failure modes that are discovered in production rather than in review. We want to replace it with something that has well-understood delivery guarantees before we add more job types to it.

Our workload is modest and well-characterized. We process roughly 30,000 jobs a day with a peak arrival rate near 40 per second, which is two orders of magnitude below what any of the candidate systems would struggle with. Sizing is therefore not the constraint that decides this — the constraints that matter are operational surface area, transactional correctness, and what the team can debug at 3am.

The transactional requirement is the sharpest of the three. Most of our jobs are enqueued as a side effect of a database write, and the two must either both happen or neither happen. An external broker cannot give us that directly, because committing to Postgres and publishing to Redis are two separate operations with a window between them; closing that window requires a transactional outbox — a table of pending messages plus a relay process that drains it into the broker. Once we have written the outbox, we have already built most of a Postgres-backed queue, and the broker becomes a component we operate in order to move rows out of a table we are also operating.

The team's experience also bears on the decision. Nobody here has run Celery in production, and Celery's failure modes — visibility timeouts, prefetch behavior, worker pools that silently stop consuming — are the kind of thing that is cheap to learn during an incident only if someone has already learned them somewhere else.

## Decision

We will implement job queueing on Postgres, using `SELECT ... FOR UPDATE SKIP LOCKED` for concurrent dequeue. Jobs live in a `jobs` table in the same database as our application data, so enqueue is an ordinary insert inside the caller's existing transaction and inherits its atomicity for free. Workers poll the table, claim rows with `SKIP LOCKED` so that concurrent workers never contend for the same job, execute, and mark the row terminal.

Retry, backoff, and scheduling logic will be written in-house rather than adopted from a framework. We estimate roughly 400 lines: an attempt counter with exponential backoff, a `run_after` timestamp for delayed and retried work, a dead-letter state for jobs that exhaust their attempts, and a reaper that returns jobs abandoned by crashed workers to the ready state.

## Consequences

The operational win is that our on-call surface does not grow. Redis would have added a second stateful system with its own persistence configuration, failure semantics, memory-pressure behavior, and upgrade path, and every one of those is a thing someone would need to understand under pressure. Keeping jobs in Postgres means backup, restore, replication, monitoring, and access control all continue to work exactly as they do today, and job state is queryable with the same tools we already use for everything else — an engineer debugging a stuck job can join it against the rows that created it.

We accept a throughput ceiling in exchange. Postgres-backed queueing degrades somewhere in the low hundreds of jobs per second, as dequeue contention and the write amplification of repeatedly updating job rows begin to compete with application traffic on the same instance. At 40 per second peak we have well over an order of magnitude of headroom, but this is the constraint most likely to force a revisit, so we should treat sustained throughput as a tracked metric rather than assume the margin holds.

We also accept the maintenance burden of the retry and scheduling code. Four hundred lines is small, but it is four hundred lines of subtle concurrent logic that a mature framework would have given us already debugged, and the edge cases — a worker that dies mid-job, a retry storm after a downstream outage, clock skew affecting `run_after` — are exactly the cases that are hard to test and expensive to get wrong. This code needs real tests and a named owner, not incidental maintenance.

Finally, long-running jobs hold a pooled connection for their duration, which couples job execution to a resource our web traffic also needs. We will mitigate this by giving workers a separate connection pool from the request path, so a batch of slow jobs cannot starve user-facing queries, and by treating any job whose runtime is measured in minutes as a candidate for decomposition into smaller units.

## Alternatives considered

**Celery with Redis** is the default answer in the Python ecosystem and brings mature scheduling, retries, routing, and a large body of operational knowledge. We rejected it because it requires adding Redis to our on-call surface, because it cannot give us atomic enqueue without an outbox that would recreate most of what we are building anyway, and because the team's lack of Celery experience turns its operational maturity into a benefit we could not immediately draw on.

**RQ** is considerably simpler than Celery and would have been easier to learn, but it shares the same Redis dependency and the same inability to enqueue transactionally, so it loses on both of the constraints that actually decided this while offering less capability than Celery in return.

## Revisiting

Reconsider this decision if sustained job throughput approaches 200 per second, if worker connection usage begins to interfere with request-path latency, or if the in-house retry and scheduling code grows materially past its current size — any of which would mean we are paying framework-sized costs without framework-sized benefits.