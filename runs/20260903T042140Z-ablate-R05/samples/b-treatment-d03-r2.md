# ADR 0014: Use Postgres `SKIP LOCKED` for background job queueing

**Status:** Accepted. Implemented in Q3 2026.

## Context

Background work is currently handled by a hand-rolled runner that polls a table, marks rows in flight with a status column, and relies on a lease timestamp to recover from crashed workers. It has no retry policy worth the name, no scheduling, and a race under concurrent workers that we have papered over with an advisory lock that serialises all dequeues. It needs to be replaced rather than extended.

Our workload is modest and well understood. We process roughly 30,000 jobs a day, with observed peaks around 40 per second, and we have no roadmap item that would change that by an order of magnitude. The jobs themselves are ordinary application work: sending mail, regenerating derived records, calling third-party APIs on a delay.

The constraint that shaped the decision most is transactionality. Nearly every job we enqueue is enqueued as part of a database write, and the job is meaningless or actively harmful if it runs against a transaction that later rolled back. We have already been bitten by the inverse case, where a commit succeeded and the enqueue was lost. Any broker that lives outside Postgres gives us this guarantee only if we build a transactional outbox in front of it, which means we would be running a Postgres-backed queue anyway, plus a relay process, plus the broker.

Operationally we are a small team with an on-call rotation that we would like to keep boring. We already run Postgres, we already have backups, failover, and monitoring for it, and the people on call already know how to debug it. Adding Redis means adding a second stateful system to that surface, including its persistence and eviction semantics, which are a common source of surprise for teams who have not tuned them before. No one on the team has run Celery in production.

## Decision

We will use Postgres as the job queue, dequeuing with `SELECT ... FOR UPDATE SKIP LOCKED` against a jobs table. Workers claim a batch of rows inside a transaction, run the work, and delete or reschedule the row on completion. Enqueueing is a plain `INSERT` in the caller's transaction, which gives us atomicity with the surrounding database writes for free and removes the need for an outbox.

## Alternatives considered

Celery with Redis is the default choice in our ecosystem and would have given us retries, scheduling, chords, and a large body of documentation without us writing any of it. We rejected it on two grounds. It requires Redis in the on-call surface for a workload that does not need Redis-level throughput, and it cannot enqueue atomically with a database commit, so we would owe ourselves an outbox regardless. The absence of Celery experience on the team compounds both: Celery's failure modes are well documented but not obvious, and we would be learning them during incidents.

RQ is a lighter answer to the same question and would have cost us less conceptual overhead than Celery. It carries the same two problems, since it is still Redis and still outside the transaction, without Celery's compensating maturity in scheduling and workflow features. Choosing it would mean accepting the operational cost of a broker while getting less back for it.

## Consequences

We accept a throughput ceiling. A Postgres-backed queue of this design runs comfortably into the low hundreds of jobs per second and then degrades, primarily through lock contention and table bloat from the delete churn. At 40 per second peak we have an order of magnitude of headroom, but this is the constraint that will eventually force a revisit.

We accept that we own the parts Celery would have given us. Retry with backoff, dead-lettering, delayed and periodic scheduling, and worker heartbeat and recovery come to roughly 400 lines of application code that we now maintain and test. The scope is bounded and the semantics are ours to define, which is worth something, but it is code that would otherwise not exist.

We accept that a running job holds a database connection for its duration, because the claim transaction stays open while the work executes. Long jobs therefore consume pool capacity that web traffic would otherwise use. We mitigate this by giving workers a separate connection pool with its own limit, so a burst of slow jobs cannot starve request handling, and by keeping a hard timeout on job execution.

Two operational obligations follow from the design. The jobs table needs autovacuum tuned more aggressively than our defaults, since high-churn queue tables bloat quickly and the dequeue query is sensitive to it. Queue depth and oldest-job age need to be on the same dashboard and alert path as our other Postgres metrics.

We should revisit this decision if sustained throughput approaches 200 jobs per second, if queue contention shows up in Postgres wait events during normal operation, or if we acquire a requirement for fan-out or workflow orchestration that our own scheduling code cannot reasonably express.