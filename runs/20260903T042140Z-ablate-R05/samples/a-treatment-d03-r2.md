# Use Postgres `SELECT ... FOR UPDATE SKIP LOCKED` for background jobs

**Status:** Accepted. Implemented in Q3.

## Context

Our background work currently runs through a job runner we wrote ourselves, and we want to replace it with something whose failure modes are understood by people other than its authors. The replacement has to serve a workload that is well characterised: roughly 30,000 jobs a day, with observed peaks around 40 jobs per second. Nothing in the roadmap suggests that figure changing by an order of magnitude, so throughput is not the dimension on which this choice turns.

Two constraints shaped the evaluation more than throughput did. The first is transactional: most of our jobs are enqueued as part of a database write, and a job that runs against a transaction that later rolled back is a correctness bug, not a retry. Any broker that lives outside Postgres can only give us that guarantee through an outbox table, which means we would be building a Postgres-backed queue anyway and then paying to relay it into a second system. The second constraint is operational. We already run Postgres, we already page on it, and adding Redis means a second stateful service in the on-call surface: its own persistence settings, its own memory pressure, its own eviction behaviour to understand at three in the morning. The team also has no Celery experience, so the option that looks most conventional on paper is the one that would cost us the most to learn and to debug under load.

We evaluated three options. Celery with Redis is the industry default and has the deepest feature set, but it brings the broker, its own operational model, and a learning curve none of us have climbed. RQ is considerably simpler than Celery while still requiring Redis, so it pays the operational cost without resolving the transactional one. Postgres queueing with `SKIP LOCKED` gives us atomic enqueue for free, since the job row is written by the same transaction as the business data, and it adds nothing to the set of systems we operate.

## Decision

Jobs are rows in a Postgres table. Workers claim them with `SELECT ... FOR UPDATE SKIP LOCKED LIMIT n`, process them, and mark them terminal in the same transaction that claimed them, so a worker that dies mid-job releases its lock and the row becomes claimable again. Producers insert job rows inside the transaction that performs the associated writes, which is what makes enqueueing atomic with the data change that motivated it.

## Consequences

We accept a throughput ceiling of a few hundred jobs per second. That is roughly an order of magnitude above our current peak, which is comfortable but not unlimited, and it is the number that should trigger a revisit rather than any qualitative dissatisfaction with the approach. If sustained load approaches that band, or if a new workload arrives with a materially different shape, the right response is to move that workload to a real broker rather than to tune the table further.

We also accept owning code that Celery would have given us. Retry with backoff, scheduled and delayed execution, and dead-lettering come to about 400 lines. This is a real maintenance obligation, and it is worth being honest that the 400 lines will grow as we discover the cases we have not thought about yet. The compensating benefit is that the logic is ours to read, and its behaviour under failure is visible in the same database we already inspect when diagnosing anything else.

Finally, a job holds a pooled connection for its entire duration, so long-running work consumes pool capacity that request handling also needs. We mitigate this by keeping worker pools separate from web pools, and by treating any job whose runtime approaches minutes as a design smell to be broken into smaller units or moved off this path entirely.

I can commit this under `docs/adr/` with the next sequence number if you tell me the numbering convention the repo uses.