# ADR-0014: Use Postgres SKIP LOCKED for Background Job Queueing

**Status:** Accepted. Implemented in Q3.

## Context

Our background work currently runs through a hand-rolled job runner that we have outgrown. It offers no durable retry semantics, no scheduling, and no visibility into what failed or why, and every new job type has meant another set of ad-hoc guards around it. We need a real queue.

The workload we are sizing for is modest: roughly 30,000 jobs a day, with observed peaks around 40 jobs per second. Nothing in our roadmap suggests an order-of-magnitude jump; the growth we expect is in job *types*, not job *rate*.

Two properties shaped the evaluation more than throughput did. The first is atomicity. A large share of our jobs are enqueued as part of a database transaction that also writes application state — a user record is created and a welcome email is queued, an invoice is finalized and a PDF render is queued. If the enqueue and the write can commit independently, we get both failure modes: jobs that fire for writes that rolled back, and writes that commit with their follow-up work silently lost. Any broker that lives outside Postgres cannot give us this directly; it requires a transactional outbox, which is a table in Postgres plus a relay process, which is most of a Postgres-backed queue with a second system bolted to the far end of it. The second property is operational surface. We run Postgres today, we know how it fails, and our on-call rotation is already calibrated to it. Adding Redis means adding a datastore with its own persistence semantics, its own failure modes, and its own place in the escalation path — and in the Celery and RQ designs, Redis holds job state we cannot afford to lose, so it is not a cache we can shrug off when it dies.

We evaluated three options: Celery with a Redis broker, RQ with Redis, and Postgres-backed queueing using `SELECT ... FOR UPDATE SKIP LOCKED`.

Celery is the most capable of the three, with mature scheduling, retries, chaining, and routing already built. It is also the most complex, and no one on the team has run it in production. Its configuration surface is large enough that the common failure mode is a subtly wrong setting discovered during an incident, and learning that surface under load is not a cost we want to take on alongside a migration. RQ is far simpler and would have been pleasant to adopt, but it inherits the Redis dependency without solving the atomicity problem, so it buys us less than Celery for the same added operational surface.

## Decision

We will implement background job queueing in Postgres, using a `jobs` table polled with `SELECT ... FOR UPDATE SKIP LOCKED` to hand out work to competing workers without contention.

Enqueueing is an `INSERT` on the same connection and transaction as the application writes that trigger it, which gives us the atomicity property for free: if the transaction rolls back, the job was never enqueued, and there is no window in which the two can disagree. Workers claim jobs in short transactions, execute outside them where possible, and mark completion or failure on a separate claim.

## Consequences

**What this costs us.** Postgres queueing has a ceiling. Somewhere in the low hundreds of jobs per second, polling and row churn on the `jobs` table start to compete with the rest of our database traffic, and past that the answer is a real broker rather than more tuning. We are choosing this at roughly a tenth of that ceiling and should treat sustained traffic above ~200 jobs/sec as the signal to revisit, not as a tuning problem — the migration is easier if we start it before we are in trouble.

We also have to write the parts Celery would have given us. Retry with backoff, scheduled and delayed execution, dead-lettering, and worker heartbeat and reclaim of abandoned jobs come to roughly 400 lines. That code is ours to maintain and ours to get right, and the subtle bugs in it — a reclaim that double-executes, a backoff that stampedes — are the kind that surface under load. We accept this because the logic is well understood and small enough to review carefully, but it is real ongoing surface, not a one-time write.

Finally, a worker executing a long-running job holds a connection from the pool for the duration. With our current job mix this is manageable, but it couples job duration to connection pressure in a way a Redis-backed queue would not, so we will run workers against a separate pool with its own bounds, and treat any job that routinely runs for minutes as a candidate for decomposition.

**What this buys us.** No new datastore on the on-call surface. Job state is visible to the same tooling, backups, replicas, and ad-hoc SQL we already use, so debugging a stuck queue is a query rather than a new set of commands. Enqueue is transactional against application state without an outbox. And the team can read the whole implementation in an afternoon, which for a system that pages us at 3am is worth more than the features we gave up.