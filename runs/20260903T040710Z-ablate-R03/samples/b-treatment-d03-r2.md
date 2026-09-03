# ADR-0014: Use Postgres SKIP LOCKED for background job queueing

**Status:** Accepted. Implemented Q3 2026.

## Context

Background work is currently handled by a runner we wrote ourselves: a table of pending work, a polling loop, and advisory locks to keep two workers from picking up the same row. It has no retry policy worth the name, no scheduled or delayed execution, and no visibility into why a job failed beyond a log line, so we have been carrying an operational tax on every incident that touches async work. We want to replace it with something that has real semantics for retries, backoff, scheduling and failure inspection, and we want to do that without changing the shape of the system more than the problem warrants.

Our volume is modest and well understood. We process roughly 30,000 jobs a day, which averages under one per second, with bursts to about 40 per second when a large customer import lands or a nightly batch fans out. Growth has been steady rather than exponential, and nothing on the roadmap changes the order of magnitude.

The requirement that constrains the choice most sharply is atomicity. Most of our jobs are enqueued as part of a database transaction that also writes the row the job operates on, and a job that runs against a transaction that later rolled back is a correctness bug, not a retry candidate. A broker outside the database cannot give us that property directly; getting it requires a transactional outbox, which means a second table, a relay process, and a new class of failure where the relay falls behind or double-publishes. That is real machinery to build and operate, and it exists only to recover a guarantee that Postgres already offers for free when the queue lives in the same database.

Two further facts about the team weigh on the decision. We already run Postgres, with backups, monitoring, failover and on-call runbooks that people have exercised. Adding Redis would add a second stateful system to that on-call surface, with its own persistence semantics, memory pressure behaviour and failure modes, staffed by the same rotation. Separately, nobody on the team has run Celery in production, and Celery's operational character, particularly around worker pools, prefetch, visibility timeouts and result backends, is not something we would learn quickly under load.

## Decision

We will queue background jobs in Postgres, using `SELECT ... FOR UPDATE SKIP LOCKED` to hand rows to workers. A job is enqueued by inserting into a jobs table inside the same transaction as the business writes that triggered it, which makes enqueue and effect commit or roll back together with no outbox and no relay. Workers poll for available rows, claim a batch under `SKIP LOCKED`, execute, and mark the outcome in the same table.

We are writing the retry, backoff and scheduling logic ourselves, which we estimate at around 400 lines: attempt counting with exponential backoff, a `run_after` column for delayed and scheduled work, a dead-letter state for jobs that exhaust their attempts, and a heartbeat so that jobs orphaned by a worker crash become claimable again.

## Consequences

The approach has a ceiling. Queueing through Postgres works well into the low hundreds of jobs per second, after which contention on the queue table and the write load of status updates start to compete with application traffic on the primary. At a peak of 40 per second we have most of an order of magnitude of headroom, but this is the constraint that will eventually force a revisit. We will treat sustained peaks above roughly 100 per second, or measurable queue-induced load on the primary, as the trigger to reopen this decision rather than waiting for saturation.

We own the retry and scheduling code, with the maintenance and correctness burden that implies. The 400 lines are not difficult, but they are load-bearing, and edge cases around clock skew, crashed workers holding stale claims, and jobs that fail after partial side effects are ours to get right and ours to test. In exchange we get code we can read in an afternoon rather than a framework whose behaviour under failure we would be inferring from documentation.

Long-running jobs hold a connection from the pool for their duration, so a handful of slow jobs can starve request-serving traffic. We are mitigating this by giving workers a separate connection pool sized independently of the web pool, and by capping the concurrency of jobs in the long-running class. Jobs that run for minutes rather than seconds should be restructured into smaller units, and we will treat a job that regularly holds a connection for more than a minute as a design problem to fix rather than a load to absorb.

## Alternatives considered

Celery with Redis is the conventional choice and offers mature retry, scheduling, routing and monitoring without us writing any of it. We rejected it on two counts: it puts Redis on the on-call rotation for a workload that does not need a dedicated broker, and it cannot give us transactional enqueue without an outbox, so the atomicity requirement would have cost us the very machinery we were hoping the framework would save us from building. The team's lack of Celery experience made the risk concrete rather than theoretical.

RQ is a lighter alternative that we liked better than Celery on complexity grounds, and it would have been a reasonable choice if Redis were already part of our infrastructure. It carries the same two objections at slightly smaller scale: it still requires Redis, and it still cannot commit atomically with our database writes. Its simplicity narrows the gap against writing our own retry logic, which weakened rather than strengthened the case for adopting it.