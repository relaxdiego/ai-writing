# ADR: Postgres `SKIP LOCKED` for background job queueing

**Status:** Accepted. Implemented in Q3.

## Context

Our background work currently runs through a job runner we wrote ourselves. It has no durable retry story, no scheduling, and no isolation between workers, and it has become the thing people page each other about. We want to replace it with a real queue.

Three things constrain the choice.

The first is volume, and it is modest: roughly 30,000 jobs a day, with peaks around 40 per second. This is small enough that throughput is not the deciding axis. Every candidate we looked at clears it.

The second is atomicity. Most of our jobs are enqueued as part of a database transaction that also writes application state, and the two must commit or fail together. A job that runs against writes that were rolled back is a correctness bug, and a write that commits without its job is a silently dropped side effect. A broker that lives outside Postgres cannot give us this directly. The standard remedy is a transactional outbox: write the job into a Postgres table inside the transaction, then relay it to the broker. That works, but it means we operate the Postgres-side queue anyway and add a relay process and a broker on top of it.

The third is operational surface. We already run Postgres, with backups, monitoring, failover and people who know how it behaves under load. Redis would be a new thing on the on-call rotation, with its own persistence and eviction semantics to learn. The team also has no Celery experience, so its configuration surface, its worker model and its failure modes would all be learned during an incident rather than before one.

## Decision

We will use Postgres as the queue, with workers claiming jobs via `SELECT ... FOR UPDATE SKIP LOCKED`.

A `jobs` table holds the queue. Producers insert rows inside the same transaction as their application writes, which gives us the atomicity requirement for free: if the transaction rolls back, the job was never enqueued. Workers poll for a batch of ready rows, lock them with `SKIP LOCKED` so that concurrent workers step past each other's claims rather than blocking, run the job, and mark it done in the same transaction that holds the lock. A worker that crashes or loses its connection releases the lock, and the row becomes claimable again with no lease timer or reaper process to maintain.

## Alternatives considered

Celery with Redis is the default answer for Python background work and has the largest body of documentation and operational lore behind it. We rejected it on the two grounds above: it adds Redis to on-call, and it needs an outbox to meet our atomicity requirement. The team's lack of Celery experience made both costs worse, since we would be learning the tool at the same time as we were learning the failure modes of the outbox we had built to work around it.

RQ is meaningfully simpler than Celery and would have been the pick if we were going to add a broker. It still adds Redis, and it still cannot commit a job atomically with a database write, so it does not resolve either of our two main objections.

## Consequences

We accept a throughput ceiling. Postgres-backed queueing degrades somewhere in the low hundreds of jobs per second, as contention on the queue table and the write amplification from row updates and vacuum start to dominate. Against a 40-per-second peak that leaves us most of an order of magnitude, which is enough for the workloads we can currently foresee but is not enough to absorb an unbounded new one.

We accept that we own the logic the brokers would have supplied. Retry with backoff, scheduled and delayed execution, dead-lettering and visibility into queue depth come to about 400 lines. This is code we have to test and maintain, and it is where bugs in this system are most likely to appear. The compensation is that it is ordinary application code in a language everyone here reads, debuggable with the same tools as the rest of the system, rather than configuration of a framework nobody has operated.

We accept that a running job holds a pooled connection for its whole duration, because the lock that protects the job is the transaction that holds the connection. This is what buys us the free crash recovery described above, and the price is that long jobs consume pool capacity. Workers therefore draw from a separate connection pool from the web tier, sized independently, so that a batch of slow jobs cannot starve request handling.

Two conditions should send us back to this decision. The first is sustained throughput climbing toward a hundred jobs per second, or queue-claim latency rising under normal load. The second is a class of job long enough that connection-hold time becomes the binding constraint on pool sizing. Either one is a reason to revisit the broker question, at which point the outbox we avoided becomes the migration path rather than an added cost: the `jobs` table is already the outbox.