# ADR 0007: Use Postgres SKIP LOCKED for background jobs

## Status

Accepted. Implemented in Q3.

## Context

We are replacing our hand-rolled background job runner. The workload it has to carry is modest: roughly 30,000 jobs a day, with peaks around 40 per second.

The requirement that shaped the evaluation is transactional. A job must become visible to workers at the moment the database writes that enqueued it commit, and must not exist at all if that transaction rolls back. A broker outside Postgres cannot offer this directly, since it has no way to participate in our database transaction. The standard remedy is an outbox: jobs are written to a Postgres table inside the business transaction, and a relay process moves those rows to the broker. The outbox restores atomicity at the cost of a second moving part, its own failure and retry behaviour, and duplicate delivery that consumers must then absorb. The enqueue path still goes through Postgres in that design, so the broker is an additional hop rather than a replacement for the database.

Our operational position also weighs on the choice. We already run Postgres with backups, monitoring, failover and an on-call rotation that knows it. Redis would be a second stateful system on that surface, with its own durability question to settle (persistence configuration, and what a failover is permitted to lose). No one on the team has run Celery in production.

## Decision

We will use Postgres itself as the queue. Jobs live in a table; workers claim them with `SELECT ... FOR UPDATE SKIP LOCKED`; enqueueing is an ordinary `INSERT` in the same transaction as the writes that caused it.

We rejected Celery with Redis. It is the most capable of the three and would carry far more throughput than we need, but it brings the largest operational and conceptual surface, its failure modes are unfamiliar to everyone here, and it still requires the outbox to meet the atomicity requirement. The capability we would be paying for is not the capability we lack.

We rejected RQ for a narrower reason. It is considerably simpler than Celery and the learning cost would be small, but it does not address the two objections that decided the question: it introduces Redis to on-call, and it needs an outbox for atomic enqueue. Simplicity in the library does not remove the second datastore underneath it.

## Consequences

Postgres queueing tops out somewhere in the low hundreds of jobs per second, which leaves us roughly five to ten times our current peak. That is real headroom but not indefinite headroom, and the migration away from it would be a project rather than a configuration change. We take sustained throughput in the low hundreds per second as the trigger to revisit this record.

We own the retry, backoff and scheduling logic that Celery and RQ ship, currently about 400 lines. We accepted this because the semantics we need are small and well understood, and because code we wrote is code we can debug at three in the morning. It is nonetheless code that needs tests and maintenance, and any growth in its ambition should be read as evidence that we chose wrong.

A long-running job holds a pool connection for its full duration, so worker concurrency is bounded by pool size and a burst of slow jobs competes with web traffic for connections. Workers should therefore draw from a connection pool separate from the application's.

Queue traffic now shows up as database load. High-churn job tables generate dead tuples at a rate the default autovacuum settings are not tuned for, so the jobs table needs its own vacuum thresholds and a watch on index bloat.

Against those costs, the queue is visible to every tool we already use. Jobs can be inspected, counted and corrected in SQL, they appear in the same backups as the rest of our data, and there is one system to keep alive rather than two.

Two items above go beyond the reasons you gave me: the vacuum consequence and the revisit trigger. Both follow from the choice rather than being part of it, and you may want them struck if the decision was recorded without them.