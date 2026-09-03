No file-write tool is available in this session, so here is the ADR inline — say the word and I'll adapt it to a path/filename convention once I can write.

---

# ADR 0001: Use Postgres `SKIP LOCKED` for background job queueing

**Status:** Accepted. Implemented in Q3.

## Context

We are replacing our hand-rolled background job runner with a real queue. Choosing one means picking a storage engine for job state, and that choice determines what we operate, what we have to build, and what transactional guarantees callers get.

Three requirements drove the decision.

**Transactional enqueue.** Most of our jobs are enqueued as part of a database write: create the record, schedule the work that follows from it. We need those to commit or roll back together. A queue that lives outside Postgres cannot give us this directly — it requires a transactional outbox, which means a second table, a relay process, and a new class of failure to reason about. If we are going to have an outbox table in Postgres anyway, the table may as well be the queue.

**Operational surface.** We already run Postgres, monitor it, back it up, and know how it fails. Redis would be a new dependency in the critical path, with its own persistence semantics, failover behavior, and on-call runbook. The team carrying the pager is the team making this decision, and nobody wanted to add a second stateful system for a queue.

**Volume.** We process roughly 30,000 jobs a day — about 0.35 per second on average, with an observed peak of 40 per second. That peak is the number that matters, and it is nowhere near the point where queue throughput is the constraint.

The team has no Celery experience.

## Decision

Store jobs in a Postgres table. Workers claim jobs with `SELECT ... FOR UPDATE SKIP LOCKED`, which lets concurrent workers pull disjoint batches without blocking each other or coordinating through a broker. Enqueue is an ordinary `INSERT` in the caller's transaction.

### Alternatives considered

**Celery with Redis.** The most capable option, and the one with the most operational weight. It adds Redis to on-call, requires an outbox to get transactional enqueue, and asks a team with no Celery experience to learn a large framework with a long history of subtle configuration pitfalls. The capability we would be buying — throughput and routing sophistication — is capability we do not need at 40 jobs per second.

**RQ.** Simpler than Celery and easier to learn, but still Redis, so it fails the same two tests: new stateful dependency, no transactional enqueue without an outbox. Simplicity was not the constraint we were solving for.

**Postgres with `SKIP LOCKED`.** Chosen. It satisfies the transactional requirement natively, adds nothing to on-call, and clears our peak load with roughly an order of magnitude of headroom.

## Consequences

### What we get

Enqueue is atomic with the writes that cause it, with no outbox and no relay. Jobs are visible to `psql`, to our existing query tooling, and to the same backup and point-in-time-recovery machinery that protects the rest of our data. There is one stateful system to operate, not two. Onboarding cost is a table schema and a claim query rather than a framework.

### What it costs

**A throughput ceiling of a few hundred jobs per second.** Beyond that, claim contention and table churn make Postgres the wrong tool. We are accepting a ceiling roughly 5–10× above our current peak. This is the load-bearing assumption of the decision; see *Revisiting* below.

**About 400 lines of retry and scheduling logic we have to write and own.** Retry with backoff, dead-lettering, visibility timeouts for crashed workers, and scheduled/delayed execution all come free with Celery and now do not. This code is ours to test and maintain, and it is the part most likely to contain bugs, because it is the part where correctness is subtle.

**Long-running jobs hold a connection from the pool.** A worker executing a job occupies a Postgres connection for the job's duration. Long jobs therefore compete with request-serving traffic for a finite resource. Mitigations available to us if this bites: a separate pool for workers, a lower per-worker concurrency, or moving genuinely long work out of the queue entirely. We are not doing any of these yet.

**Queue traffic is now database traffic.** Job table churn produces dead tuples and competes for I/O with application queries. Autovacuum settings on the jobs table will need attention that a Redis-backed queue would not have required.

### Revisiting

Reopen this decision if sustained throughput approaches ~150 jobs per second, if pool contention from long-running jobs starts affecting request latency, or if we find ourselves reimplementing large parts of a broker — fan-out, complex routing, priority classes with independent workers. The first two are measurable; we should alert on them rather than wait to notice. Migration away from this design is bounded: the enqueue API stays, the claim query is replaced, and the retry logic we wrote is the part that gets thrown away.