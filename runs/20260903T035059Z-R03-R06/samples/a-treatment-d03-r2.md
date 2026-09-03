# ADR-XXX: Postgres SKIP LOCKED for background jobs

## Status

Accepted. Implemented in Q3.

## Context

Background work currently runs through a job runner we wrote ourselves. Its locking, retry and scheduling behaviour accreted one job type at a time, so the semantics under failure are whatever the code happens to do rather than anything we specified, and adding a job type means reading the runner first. We want to replace it with a queue whose failure behaviour is stated up front, and the question is what to build that on.

Our volume is modest and not growing quickly: roughly 30,000 jobs a day, with peaks around 40 per second. Every option under consideration clears that by a wide margin, so throughput headroom did not discriminate between them and we did not weight it.

The binding constraint is atomicity. Most jobs are enqueued inside a database transaction that also writes the rows the job will later read. If the enqueue can succeed while the transaction rolls back, or the reverse, we get jobs that fire against state that never committed and writes that commit with no job to follow them. A separate broker cannot give us this directly; the standard remedy is a transactional outbox, which means a table of pending messages in Postgres plus a relay process that drains it into the broker. That is most of a Postgres-backed queue already, with a second system behind it and a second set of delivery semantics to reason about.

Two further considerations pointed the same way. We operate Postgres today, with backups, monitoring, failover and people who have been paged for it; Redis would be a second stateful system on the on-call surface, with its own persistence configuration and its own failure modes to learn. And nobody on the team has run Celery in production. Celery's configuration surface is where its operational trouble concentrates: result backends, prefetch counts, `acks_late`, and visibility timeouts that interact badly with long tasks. We would be learning that surface during incidents.

## Decision

We will use Postgres as the queue, claiming work with `SELECT ... FOR UPDATE SKIP LOCKED`.

A `jobs` table holds queued work. Enqueue is an `INSERT` on the caller's connection, inside the caller's transaction, so a job becomes visible exactly when the writes it depends on commit and never before. Workers claim small batches under `SKIP LOCKED`, marking rows as running with a lease timestamp; a job whose lease expires without a heartbeat is returned to the queue, which is how we recover from worker crashes. Retries use an attempt counter and an exponential backoff written into a `run_after` column, which also gives us delayed and scheduled jobs with no extra machinery. This is about 400 lines of application code plus the migration.

## Alternatives considered

Celery with Redis is the default answer in this ecosystem and would have given us retries, scheduling via beat, and a large body of documentation for free. It fails the atomicity requirement without an outbox, adds Redis to on-call, and lands the team on an unfamiliar and configuration-heavy runtime.

RQ is considerably simpler than Celery and would have been a smaller thing to learn, but it still requires Redis and still cannot enlist in our transactions, so it carries the two costs that decided the question while giving up Celery's maturity in exchange for the one we did not care about.

## Consequences

Postgres queueing stops scaling somewhere around a few hundred jobs per second, an order of magnitude above our peak. We accept that our current growth curve does not reach it, and we treat sustained throughput above roughly 150 per second as the signal to revisit this record rather than to tune the implementation.

We own the retry and scheduling logic, including the tests for lease expiry, redelivery and backoff. This is code we would not have written under Celery, and every bug in it is ours to find.

Long-running jobs hold a pooled connection for their duration, which couples worker concurrency to database connection limits in a way a broker-based system avoids. Workers will therefore draw from a separate pool sized independently of the web application's, so that a burst of slow jobs cannot starve request handling.

A high-churn queue table also produces dead tuples faster than the rest of our schema, so the table needs its own autovacuum settings and a place in whatever we watch for bloat. Failing to do this degrades claim latency gradually rather than visibly, and it is the most likely way for this design to disappoint us in the first year.