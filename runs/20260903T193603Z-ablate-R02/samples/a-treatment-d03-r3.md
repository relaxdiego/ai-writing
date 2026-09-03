# Background jobs on Postgres with SELECT ... FOR UPDATE SKIP LOCKED

**Status:** Accepted. Implemented in Q3.

## Context

Our background work currently runs on a hand-rolled runner that we want out of the codebase. Choosing its replacement came down to three candidates: Celery with Redis as the broker, RQ (also on Redis), and a queue held in our existing Postgres database, with workers claiming rows using `SELECT ... FOR UPDATE SKIP LOCKED`.

Three facts about our situation decided it. First, our volume is modest: roughly 30,000 jobs a day, peaking around 40 per second. Second, a job must become visible to workers exactly when the database writes that enqueued it become visible, and never otherwise. An external broker cannot give us that, because the enqueue and the commit are two systems and two failure windows; recovering the guarantee means building a transactional outbox, at which point we are already running a queue in Postgres and paying for Redis as well. Third, we already operate Postgres, and we run our own on-call. Adding Redis adds a datastore that has to be sized, backed up, monitored, patched, and understood at three in the morning by whoever is holding the pager. Nobody on the team has run Celery before, so its operational surface would be new alongside the broker's.

## Decision

Jobs live in a Postgres table in the application database. Workers claim them by polling with `SELECT ... FOR UPDATE SKIP LOCKED`, which lets concurrent workers take disjoint sets of rows without blocking on each other. Enqueueing is an ordinary `INSERT` inside the caller's transaction, so a job exists if and only if the work that created it committed.

Retry policy, backoff, scheduled and delayed execution, and dead-lettering are ours to write: about 400 lines against the same table.

## Consequences

The costs we are accepting, knowingly:

- The design does not scale past roughly a few hundred jobs per second. At 40 per second peak we have close to an order of magnitude of headroom, but this is the constraint that will eventually force a revisit. Sustained throughput above about half the ceiling should be treated as the signal to start that work rather than as a capacity problem to tune around.
- We own the retry and scheduling logic, including its bugs. Celery's equivalent is battle-tested and ours will not be, so it needs real tests around backoff, visibility timeouts, and crash recovery of in-flight jobs.
- A long-running job holds a database connection for its duration. Workers therefore get a connection pool separate from the web tier's, sized so that a batch of slow jobs cannot starve request handling.

In exchange, our production dependency count does not change, deployment is a migration rather than a new service, and failed jobs are inspectable with the same SQL and the same tooling as the rest of our data.

## Alternatives

Celery with Redis was the strongest option on features: mature retries, scheduling, routing, and a large body of operational knowledge to draw on. It lost on the two things we weighted most, the added broker on our on-call surface and the absence of transactional enqueueing, and the team's lack of experience turned its maturity into an advantage we could not immediately collect.

RQ is simpler than Celery and would have been cheaper to learn, but it still requires Redis and still cannot enqueue inside our transaction. Having decided Redis was the cost we did not want to pay, RQ had nothing left to offer over the Postgres approach.