# ADR 0000: Use Postgres SKIP LOCKED for background job queueing

Status: Accepted. Implemented in Q3 2026.

## Context

Background work is currently handled by a hand-rolled runner that we want to retire. Our volume is modest and well understood: roughly 30,000 jobs a day, with peaks around 40 per second. Nothing in the roadmap suggests that figure changing by an order of magnitude.

The requirement that constrains the choice most tightly is atomicity. Jobs are enqueued by the same transactions that perform the database writes those jobs depend on, and we need the two to commit or fail together. A broker that lives outside Postgres cannot give us that directly; getting it back means writing the enqueue into a Postgres outbox table and running a relay process that forwards rows to the broker. The outbox is a well-understood pattern, but it is a second piece of infrastructure whose failure modes (relay lag, duplicate publishes, replay after crash) we would be taking on in exchange for a broker we do not otherwise need.

Two other facts shaped the decision. We already operate Postgres, with backups, monitoring, failover and on-call runbooks in place, and adding Redis would widen the on-call surface with a service nobody currently carries a pager for. And no one on the team has run Celery in production, so its operational model, from prefetch and acknowledgement semantics through to result backends, would be learned under load rather than before it.

## Decision

We will queue jobs in Postgres, using `SELECT ... FOR UPDATE SKIP LOCKED` for worker dequeue. Enqueueing is an ordinary insert inside the caller's transaction, so a job becomes visible to workers exactly when the writes it depends on become visible, and a rolled-back transaction leaves no job behind. Retry, backoff and scheduling are implemented in application code against the same table.

## Consequences

The atomicity requirement is satisfied without an outbox, a relay, or any reconciliation between two stores. Enqueueing needs no new client library and no new failure path: if the transaction commits, the job exists. On-call inherits nothing new, and the queue is inspectable with the same tools, credentials and dashboards the team already uses for the rest of the database, which also means a stuck or backed-up queue is visible as an ordinary table query.

Against that we accept three costs. The first is a throughput ceiling. Postgres-backed queueing runs out of room somewhere in the low hundreds of jobs per second, since every dequeue is a write against a contended table and the row churn feeds autovacuum. Our peak of 40 per second sits an order of magnitude below that, so the headroom is real but finite, and growth in job volume will consume it faster than growth in traffic generally does.

The second is roughly 400 lines of retry and scheduling logic that a mature broker would have supplied: attempt counting, exponential backoff, dead-lettering, visibility timeouts for workers that die mid-job, and the periodic sweep that reclaims them. This is code we own, test and debug, and its edge cases (a worker that hangs rather than crashes, a job whose handler is not idempotent) are ours to get right.

The third is connection pressure. A worker holds a Postgres connection for the lifetime of a job, so a long-running job occupies a pool slot for its whole duration. Worker pools must therefore be sized and bounded separately from the web pool, and jobs that block on slow external calls will hold connections while doing no database work.

We should revisit this decision if sustained throughput approaches a couple of hundred jobs per second, if job durations grow enough that connection occupancy becomes the binding constraint, or if we take on Redis for another reason and the marginal cost of a broker drops.

## Alternatives considered

Celery with Redis is the most capable option and brings retries, scheduling, routing and chaining without our writing any of it. It fails on the two points that matter most here: Redis becomes a new on-call dependency, and the enqueue cannot join our database transaction, so we would need an outbox to preserve atomicity and would be running both a broker and a relay. The absence of Celery experience on the team compounds this, since its operational semantics are subtle in exactly the places that bite under failure.

RQ is markedly simpler than Celery and would have been easier to learn, but it does not address the objection that drove the decision. It still requires Redis, and it still cannot make the enqueue atomic with our writes, so it carries the same infrastructure cost as Celery while offering less in return.