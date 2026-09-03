# ADR-014: Use Postgres `SKIP LOCKED` for background job queueing

Status: accepted; implemented in Q3.

## Context

Background work currently runs through a job runner we wrote ourselves: a table of pending work, a polling loop, and a set of conventions that each service applies slightly differently. It has no real retry semantics, no scheduling, and no visibility into why a job failed, and every new consumer reinvents a little more of it. We want to replace it with something with defined delivery and retry behaviour before it grows further.

The workload is modest and well understood. We process roughly 30,000 jobs a day with an observed peak of about 40 per second, and the growth curve over the last year does not suggest an order-of-magnitude change. Almost all of these jobs are enqueued as part of a request that is already writing to Postgres, which matters more than the volume does: if a job is enqueued and the surrounding transaction then rolls back, the job runs against state that never existed, and if the transaction commits but the enqueue fails, the work is silently dropped. Our current runner gets this right by accident, because its queue table lives in the same database, and we do not want to give that property up.

We also have to weigh operational cost. We run Postgres, we have on-call rotations and runbooks for it, and we understand its failure modes. Adding a broker means adding a second stateful system to the on-call surface, with its own persistence configuration, its own memory behaviour under backlog, and its own upgrade path. No one on the team has run Celery in production.

## Decision

We will queue jobs in Postgres, using `SELECT ... FOR UPDATE SKIP LOCKED` to hand out work to competing consumers. Workers claim a batch of rows inside a transaction, process them, and mark them complete; rows locked by another worker are skipped rather than waited on, which is what makes multiple workers safe without an external coordinator. Enqueueing is an ordinary `INSERT` on the same connection as the business writes, so a job becomes visible exactly when the data it depends on becomes visible.

We will write the retry, backoff, and scheduling layer ourselves. The estimate is about 400 lines: attempt counters and a maximum, exponential backoff with jitter expressed as a `run_after` timestamp, a dead-letter state for exhausted jobs, and a claim timeout so that work orphaned by a crashed worker becomes visible again.

## Alternatives considered

Celery with Redis is the default answer in this ecosystem and has the deepest feature set, including scheduling, chords, and routing we would otherwise build. It costs us a Redis instance in the critical path, a broker whose durability story depends on configuration we would have to get right and keep right, and a framework with a large surface area that nobody here has debugged under load. It also does not solve the atomicity problem. Enqueueing to a separate broker inside a database transaction gives us a message that can outlive a rollback, so a correct implementation needs an outbox table in Postgres with a relay process, at which point we are running the Postgres queue machinery anyway plus Redis on top of it.

RQ is considerably simpler than Celery and would have been a smaller thing to learn, but it carries the same two structural problems: it requires Redis, and it cannot participate in our transactions. Simplicity was not the binding constraint.

## Consequences

The atomicity property is the main thing we gain. Enqueue and commit are one operation, there is no outbox, and there is no window in which the two systems disagree. Operationally we add no new component: workers are processes that talk to the database we already monitor, back up, and know how to restore, and a failed job is a row we can query with the same tools we use for everything else.

The ceiling is real and we are accepting it deliberately. Queueing through Postgres degrades somewhere in the low hundreds of jobs per second, as claim contention and table churn start to compete with ordinary application traffic, which leaves us most of an order of magnitude of headroom against our current peak. The trigger for revisiting this decision is sustained throughput above roughly 150 jobs per second, or vacuum pressure from the queue table showing up in query latency for unrelated tables, whichever comes first. Because the enqueue and claim operations sit behind a small interface, swapping the backend later is a contained change rather than a rewrite.

We own the retry and scheduling logic, including its bugs. This code needs tests for the cases that are easy to get wrong: a worker that dies mid-job, a job that exceeds its claim timeout while still running, and backoff that does not synchronise retries into a thundering herd. It will also lack features we might want later, such as job chaining and rate limiting per queue, and we should build those only when something concrete needs them.

Long-running jobs hold a pooled connection for their duration, so a slow job class can starve the pool that serves web requests. We mitigate this by giving workers a separate connection pool and database role from the application, capped independently, and by treating any job that regularly runs longer than about thirty seconds as a candidate for splitting into chunks. A job that must run for minutes should release its claim and re-enqueue a continuation rather than hold a connection open across the whole run.