# ADR-0014: Use Postgres `SKIP LOCKED` for background job queueing

**Status:** Accepted. Implemented in Q3.

## Context

Background work is currently handled by a job runner we wrote ourselves: a table of pending work, a polling loop, and an advisory-lock scheme to keep two workers from picking up the same row. It has held up, but it has no retry policy worth the name, no scheduled or delayed execution, and no visibility into why a job failed. Rather than continue extending it, we evaluated moving to something with an established operational story.

Three requirements shaped the evaluation. First, jobs must become visible to workers only if the transaction that enqueued them commits, and must always become visible if it does. A user signs up, we write the user row and enqueue a welcome email, and neither half may survive without the other. Second, our volume is modest and expected to stay that way: roughly 30,000 jobs a day, with bursts to about 40 per second. Third, we have a small on-call rotation that currently pages on Postgres and the application tier, and nobody on the team has run Celery in production.

## Decision

We will use Postgres as the queue, with workers claiming jobs via `SELECT ... FOR UPDATE SKIP LOCKED` against a jobs table in the primary database.

The atomicity requirement is the argument that decided it. A separate broker cannot participate in our database transaction, so getting the same guarantee from Redis would mean writing an outbox: a table of pending publishes, a relay process draining it into Redis, and the deduplication that at-least-once relay delivery forces on every consumer. That is a queue implementation on top of Postgres plus a second queue, which is strictly more machinery than the queue on top of Postgres alone. With `SKIP LOCKED`, the enqueue is an `INSERT` in the same transaction as the writes it accompanies, and the guarantee is free.

The volume figures make the tradeoff easy. Postgres queueing runs out somewhere in the low hundreds of jobs per second, which leaves close to an order of magnitude of headroom above our peak, and our peak is bursty rather than sustained. Adding Redis would put a second stateful system on the on-call surface, with its own persistence configuration, failover behaviour and memory limits, to buy throughput we have no use for.

## Alternatives considered

**Celery with Redis** is the default choice in our language ecosystem and has the richest feature set: retries, scheduling, chains and chords, and a mature worker model. It loses on the two axes we care about. It requires the outbox described above to give us transactional enqueue, and no one on the team has operated it, so the failure modes that make Celery notorious (lost tasks on broker restart, workers wedged on prefetch, the visibility timeout interacting badly with long jobs) would all be learned during incidents.

**RQ** is considerably simpler than Celery and would have been a smaller thing to learn, but it still requires Redis and therefore still requires the outbox. Having paid that cost, we would have less than Celery offers.

## Consequences

We accept a throughput ceiling of a few hundred jobs per second. Beyond that, the polling and row-locking load begins to compete with application queries on the same instance, and the answer would be to move the jobs table to a separate Postgres instance or to migrate to a real broker. We should treat sustained throughput above 200 per second as the trigger to revisit this record rather than waiting for contention to show up as latency on user-facing queries.

We take on roughly 400 lines of retry, backoff and scheduling logic that Celery would have provided. This is the part of the decision most likely to be regretted: the code is easy to write and easy to get subtly wrong, particularly around retry storms after a downstream outage and around jobs that fail between claim and completion. It needs tests that exercise worker death mid-job, and it needs a dead-letter path from the outset rather than added after the first incident.

Long-running jobs hold a pooled connection for their duration, since the claiming transaction stays open while the job runs. This couples job duration to pool capacity in a way that a broker would not, and it means a handful of slow jobs can starve the pool that serves web requests. We are mitigating it by giving workers a separate pool from the web tier and setting a hard job timeout, but the constraint is real and argues for keeping jobs short.

In exchange we add nothing to the on-call surface, we get exactly-once enqueue semantics without a relay, and inspecting the queue is a `SELECT` that anyone on the team already knows how to write.