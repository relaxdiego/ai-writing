# Use Postgres `SKIP LOCKED` for background jobs

**Status:** Accepted. Implemented in Q3 2026, replacing the hand-rolled job runner.

## Context

Our background work runs on a job runner we wrote ourselves, and we are replacing it with a real queue. The workload it has to carry is modest: roughly 30,000 jobs a day, with observed peaks around 40 jobs per second. Nothing in the roadmap suggests that figure changes by an order of magnitude within the life of this decision.

The requirement that shaped the evaluation is transactional. Most of our jobs are enqueued as part of a database write, and the job must not become visible to a worker unless that write commits, nor be lost if it does. With a broker that lives outside Postgres, the enqueue and the write are two separate commits, so we would have to close the gap with a transactional outbox: a table of pending messages written in the same transaction, plus a relay process that drains it into the broker. That is a second queue in front of the queue, with its own failure modes and its own on-call story.

Two facts about the team matter as much as the technical ones. We already run Postgres in production and know how it fails, and adding Redis would put a second stateful system on the on-call surface for a workload that does not obviously need one. Nobody on the team has run Celery before, so the option that looks most capable on paper is also the one whose operational edges we would be learning during incidents.

## Options considered

| | Celery + Redis | RQ + Redis | Postgres `SKIP LOCKED` |
|---|---|---|---|
| New system on-call | Redis | Redis | none |
| Atomic with enqueueing write | only via outbox | only via outbox | native |
| Practical throughput | tens of thousands/s | thousands/s | a few hundred/s |
| Retry, scheduling, backoff | built in | partly built in | we write it |
| Team experience | none | none | Postgres, yes |

Celery is the most capable of the three and the most operationally expensive for us. It brings mature retry, scheduling, chords and routing, and it would carry our volume with room to spare, but it also brings a broker, a worker model with a good deal of surface area, and a body of operational lore that we do not have. RQ is meaningfully simpler and would have been a reasonable choice on a team that already ran Redis; it still requires Redis, still requires an outbox to get atomicity, and its scheduling and retry story is thin enough that we would be writing some of the same code we are writing anyway.

Queueing in Postgres with `SELECT ... FOR UPDATE SKIP LOCKED` gives us the atomicity requirement for free, because the enqueue is an ordinary insert in the transaction that already exists. Workers claim rows by locking them and skipping rows other workers hold, which is exactly the primitive a queue needs, and a crashed worker releases its lock when its connection dies. What it does not give us is anything above that primitive.

## Decision

We queue jobs in Postgres, claiming them with `SKIP LOCKED`, and we write the retry, backoff and scheduling logic ourselves. No new broker enters the stack.

## Consequences

The costs we are accepting, and accepting knowingly:

- **Throughput ceiling.** Postgres queueing does not scale much past a few hundred jobs per second, since every claim is a write against a hot table and every completion is another one. Our 40/s peak leaves a margin of roughly five to ten times, which is comfortable but is not the kind of headroom that absorbs a change of business model.
- **Code we own.** Retry counts, exponential backoff, dead-lettering, delayed and scheduled execution and visibility timeouts come to about 400 lines. That code is ours to test, to debug and to keep correct, and it is the part of this decision most likely to be underestimated.
- **Connection pressure.** A long-running job holds a pooled connection for its whole duration, because the row lock is the claim. Workers therefore get a separate pool sized for concurrency rather than sharing the web application's, and jobs that run for minutes rather than seconds need to be looked at individually.

Against those, the enqueue path becomes simpler than any broker-based design could be: no outbox, no relay, no reconciliation between two stores, and job state is queryable with the same SQL and visible to the same backup and point-in-time recovery we already run. Debugging a stuck job is a `SELECT`.

We should revisit this decision if sustained throughput approaches 200 jobs per second, if job-table write load becomes a measurable component of database contention for user-facing queries, or if the hand-written scheduling logic grows past roughly twice its current size. The migration path at that point is to move execution to a broker while keeping the jobs table as the outbox, which is work we have deliberately deferred rather than avoided.