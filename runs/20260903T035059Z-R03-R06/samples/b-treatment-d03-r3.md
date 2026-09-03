# ADR 0007: Postgres SKIP LOCKED for background job queueing

**Status:** Accepted; implemented in Q3.

## Context

We are replacing a hand-rolled background job runner with a real queue. The requirements that shaped the choice were operational rather than architectural. We already run Postgres and page on it, and adding Redis would mean a second stateful system in the on-call rotation, with its own failure modes, persistence configuration and upgrade path. Our volume is modest: roughly 30,000 jobs a day, with observed peaks around 40 per second, which is a fraction of what any of the candidates can absorb, so throughput was not a discriminator. The requirement that did discriminate was atomicity. Most of our jobs are enqueued as a consequence of a database write, and a job that runs against a transaction that later rolled back, or that is silently lost when the write succeeds and the enqueue does not, produces exactly the class of inconsistency we are trying to remove. A separate broker cannot give us that property directly; it requires a transactional outbox, which is a table, a relay process and a delivery-ordering problem on top of the broker we would have just adopted. Finally, no one on the team has run Celery in production, and its configuration surface is large enough that learning it during an incident is a real cost.

## Decision

We will queue jobs in Postgres, using a `jobs` table and `SELECT ... FOR UPDATE SKIP LOCKED` for claiming. Workers poll for claimable rows, take them under a row lock, and mark them terminal in the same transaction that commits the job's own writes where possible. Producers insert the job row inside the transaction that performs the business write, so enqueue and write commit or fail together with no outbox.

We evaluated Celery with Redis, RQ, and this option. Celery brings mature scheduling, retries and routing, but it costs us the Redis dependency and lands the operational and conceptual load on a team with no prior exposure to it. RQ is much simpler and we would learn it quickly, but it carries the same Redis dependency for a smaller feature return, and it still leaves the atomicity problem unsolved. Both broker options would have required the outbox we were trying to avoid.

## Consequences

We accept a throughput ceiling of roughly a few hundred jobs per second. That is five to ten times our current peak, which is comfortable but not unlimited; a change in product shape that makes jobs cheap and numerous, such as per-recipient fanout on a large mailing, could consume that headroom quickly.

We accept writing our own retry and scheduling logic, estimated at about 400 lines: attempt counting, backoff, a visibility timeout for workers that die mid-job, and a scheduled-for column with the corresponding index. This is code we own and must test, and it is the part of the decision most likely to be wrong in its details rather than in its direction.

We accept that long-running jobs hold a connection from the pool for their duration, since the row lock lives on the claiming transaction. This couples worker capacity to pool sizing and makes a slow job class capable of starving request-serving connections. Worker pools should be sized against the Postgres connection budget rather than against CPU, and jobs expected to run for minutes should be split or moved off this path.

In return, the queue is visible to SQL, covered by our existing backups and replication, and adds nothing to the on-call surface.

## Revisit criteria

Reopen this decision if sustained enqueue rate approaches 200 jobs per second, if queue polling becomes a measurable share of database load, or if connection pool exhaustion traced to long-running jobs recurs after the mitigations above.