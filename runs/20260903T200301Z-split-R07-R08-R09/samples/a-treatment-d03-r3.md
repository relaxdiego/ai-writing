# Use Postgres SKIP LOCKED for background job queueing

**Status:** Accepted. Implemented in Q3.

## Context

Our background work currently runs through a hand-rolled job runner that we have outgrown, and we want to replace it with something with real queue semantics: durable enqueue, at-least-once delivery, retries, and scheduled execution. The replacement has to fit three constraints that are already fixed for us.

The first is operational. We run Postgres today and the on-call rotation knows how to reason about it. Adding a broker means adding a second stateful system to the paging surface, with its own failure modes, persistence configuration, and upgrade path, staffed by the same people.

The second is volume. We process roughly 30,000 jobs a day, which averages well under one job per second, with observed peaks around 40 per second. We have no projection that takes us near an order of magnitude above that within the lifetime of this decision.

The third is transactional. A large share of our jobs are enqueued as part of a database write, and the job must not become visible to a worker unless that write commits, nor be lost if it does. Any broker that lives outside Postgres can only give us this through a transactional outbox, which means we would be building and operating a Postgres-backed queue anyway, as a staging table in front of the real one.

The team also has no operational experience with Celery. Its configuration surface, its result-backend and broker semantics, and its failure behaviour under partial outages are all things we would be learning during an incident rather than before one.

## Decision

We will implement job queueing in Postgres, using a jobs table and `SELECT ... FOR UPDATE SKIP LOCKED` for worker claim. Workers claim a batch of due rows, run them, and mark the outcome inside the same transaction that holds the lock, so a worker that dies releases its claims when its connection drops.

Enqueue is an ordinary `INSERT` in the caller's transaction. This is the property that decided the evaluation: the job and the data it operates on commit or roll back together, with no outbox, no dual write, and no window in which a worker can pick up a job describing a row that does not exist.

## Consequences

We accept the following costs, all of which we consider bounded and visible.

- **A throughput ceiling of a few hundred jobs per second.** Beyond that, lock contention and table churn on the claim path stop being manageable by tuning. At a 40 per second peak this leaves us most of an order of magnitude of headroom, and the ceiling is high enough that we will see sustained growth toward it in our own metrics long before we hit it.
- **Retry and scheduling logic we write ourselves,** estimated at around 400 lines: attempt counting, backoff, dead-lettering, and a due-at column with the index to support it. This is code we own and must test, but it is small, it is ordinary, and its behaviour is inspectable in SQL rather than distributed across a broker's configuration.
- **Long-running jobs hold a connection from the pool** for their full duration, because the claim lock lives in the worker's transaction. Worker capacity is therefore bounded by connection capacity, and a slow job class can starve the pool. We are mitigating this by giving workers a separate pool from request-serving traffic. If a job class emerges whose runtime makes even a dedicated pool uneconomic, the escape is a lease column with a visibility timeout instead of a held lock, which costs us the automatic release on worker crash and requires a reaper. We are not building that now.

Against those costs we get one Postgres to operate, back up, and page on; queue state that is queryable with the same tools and the same credentials as the rest of our data, including in an incident; and atomic enqueue with no outbox to maintain.

## Alternatives considered

Celery with Redis was rejected on the on-call and unfamiliarity grounds above, and because the transactional requirement would have forced an outbox on top of it. RQ is materially simpler than Celery and the team could have learned it quickly, but it still introduces Redis as a second stateful dependency and still cannot commit a job atomically with the write that produces it, so it pays the same operational price for the same missing property.

## Revisiting

We should reopen this decision if sustained throughput passes roughly 100 jobs per second, if we take on a job class with runtimes long enough that connection-holding drives worker capacity, or if we add Redis to the stack for unrelated reasons and the marginal on-call cost of a broker drops to near zero.