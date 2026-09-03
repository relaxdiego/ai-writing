# ADR 0014: Use Postgres `SKIP LOCKED` for background job queueing

**Status:** Accepted. Implemented in Q3 2026, replacing the hand-rolled runner.

## Context

Background work is currently handled by a runner we wrote ourselves, which polls a table, marks rows in place, and offers no retry policy, no scheduling, and no isolation between a job that fails and the process that ran it. It has reached the point where every new job type requires a small amendment to the runner, and we want a queue with defined semantics instead.

Three properties of our situation shape the choice. The first is operational: we already run Postgres, with backups, monitoring, failover, and an on-call rotation that understands it. Adding Redis means adding a second stateful system to that rotation, including its persistence configuration and its failure modes, for a workload that does not otherwise need it. The second is volume: we process roughly 30,000 jobs a day with a peak around 40 per second, which is small enough that throughput is not the constraint on the design. The third is transactional: most of our jobs are enqueued as a consequence of a database write, and the two must either both happen or neither happen. A user signs up and we send a welcome email; an order is placed and we schedule fulfilment. With a broker outside the database, the enqueue and the write are separate commits, and closing that gap correctly requires a transactional outbox, which is a second queue implementation sitting in front of the first one.

The team also has no Celery experience. That is not decisive on its own, but it changes what "use the standard tool" costs us, because the standard tool has a large configuration surface and its failure modes are learned rather than read.

## Decision

We will queue jobs in a Postgres table and dequeue them with `SELECT ... FOR UPDATE SKIP LOCKED`, which lets each worker claim a batch of rows without blocking on rows another worker has already claimed. Workers poll on a short interval, claim a small batch inside a transaction, execute, and mark completion or schedule a retry.

Enqueueing is an ordinary `INSERT` performed on the same connection and inside the same transaction as the business writes that cause it. This is the point of the decision: the job becomes visible to workers exactly when the data it operates on becomes visible, and a rolled-back transaction leaves no orphaned job behind. No outbox, no reconciliation job, no window in which the two stores disagree.

## Consequences

We accept a throughput ceiling in the low hundreds of jobs per second. Beyond that, polling and row contention make Postgres the wrong substrate, and the fix is a real broker rather than tuning. Our peak is 40 per second, so we have roughly an order of magnitude of headroom, and we will treat sustained load above 200 per second as the signal to reopen this decision rather than waiting for the ceiling to arrive as an incident.

We take on ownership of retry and scheduling logic, estimated at about 400 lines: exponential backoff with jitter, a maximum attempt count, a dead-letter table, visibility timeouts so a worker that dies mid-job releases its claim, and support for jobs scheduled at a future time. This is code we must test and maintain, and it is the part of the decision most likely to be underestimated. It is also code we can read in one sitting, which is the compensating benefit.

Long-running jobs hold a connection from the pool for their duration. Workers will therefore use a connection pool separate from the one serving web requests, sized independently, so that a slow job cannot starve request handling. Jobs expected to run for minutes should release their claim transaction and use a heartbeat column rather than holding an open transaction for the whole execution, since long transactions also delay vacuum and inflate table bloat on the queue table itself.

## Alternatives considered

Celery with Redis is the default answer in our ecosystem and would have given us retries, scheduling, and a result backend without writing them. It fails on the two constraints we care most about: it puts Redis in the on-call rotation, and it cannot make the enqueue atomic with the database write without an outbox, which reintroduces the Postgres queue we were trying to avoid while keeping the broker as well. The absence of team experience made its large surface area a further cost rather than a saving.

RQ is simpler than Celery and would have been a smaller thing to learn, but it still depends on Redis and so carries the same operational and atomicity problems, without the maturity and ecosystem that justify Celery's complexity when someone does need it.