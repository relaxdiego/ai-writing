I don't have filesystem tools in this session, so here's the ADR as text — paste it into your `docs/adr/` (or wherever the existing design record lives) and renumber the heading to match your sequence.

---

# ADR-NNN: Use Postgres `SKIP LOCKED` for background job queueing

**Status:** Accepted — implemented in Q3

## Context

Background work is currently handled by a hand-rolled job runner. We want to replace it with a real queue.

Our constraints:

- **We already operate Postgres.** We do not operate Redis. Adding it means adding a datastore to the on-call surface: persistence configuration, failover behavior, memory limits, and a second thing to page someone about at 3am.
- **Job volume is modest.** About 30,000 jobs/day, which averages well under one job per second, with an observed peak of 40 jobs/second.
- **Enqueue must be atomic with the database write that causes it.** When a request writes rows and schedules follow-up work, either both happen or neither does. A queue that lives outside Postgres cannot give us this directly — it requires a transactional outbox, which is a table in Postgres plus a relay process, i.e. most of the complexity of a Postgres queue *in addition to* the broker.
- **No one on the team has run Celery in production.** Celery's failure modes (visibility timeouts, prefetch behavior, result backend semantics, broker-specific edge cases) are learned expensively and usually during an incident.

We evaluated three options: Celery with Redis, RQ, and a Postgres table polled with `SELECT ... FOR UPDATE SKIP LOCKED`.

## Decision

We will implement job queueing as a Postgres table consumed with `SELECT ... FOR UPDATE SKIP LOCKED`.

Enqueue is an ordinary `INSERT` inside the caller's existing transaction. Workers claim jobs by selecting a batch of ready rows with `SKIP LOCKED`, which lets concurrent workers take disjoint sets of rows without blocking each other.

## Alternatives considered

**Celery + Redis.** The most capable option and the one with the most operational literature. Rejected on two grounds: it adds Redis to on-call for a workload that does not need Redis's throughput, and it cannot deliver transactional enqueue without an outbox, so the atomicity requirement is unmet or is met by building a Postgres queue anyway. The team's lack of Celery experience made this worse — we would be paying an operational learning cost for capacity we do not need.

**RQ.** Simpler than Celery and easier to learn, but it is also Redis-backed, so it fails on the same two counts: new datastore, no transactional enqueue. The simplicity advantage over Celery does not address either of our actual constraints.

**Postgres `SKIP LOCKED`.** Chosen. Satisfies the atomicity requirement by construction, adds no new operational surface, and has adequate headroom for our volume.

## Consequences

### What we get

- Enqueue is transactional with application writes at no additional cost. No outbox, no relay, no dual-write reconciliation.
- No new datastore in the on-call rotation. Backups, failover, monitoring, and access control are the ones we already have.
- Jobs are inspectable and mutable with SQL. Debugging a stuck queue is a `SELECT`, and requeueing is an `UPDATE`.
- No new library semantics for the team to learn under pressure.

### Costs we are accepting

- **Throughput ceiling of roughly a few hundred jobs/second.** At a 40/s peak we have somewhere around 5–10x headroom. This is comfortable but not unlimited: it is a capacity decision with a known expiry, not a permanent one. If sustained throughput approaches triple digits per second, this ADR should be revisited rather than tuned around.
- **We write our own retry and scheduling logic — roughly 400 lines.** Retry counts, backoff, dead-lettering, visibility/lease expiry for crashed workers, and scheduled/delayed execution are all ours to build, test, and maintain. This code is load-bearing and deserves the same test coverage as application logic.
- **Long-running jobs hold a connection from the pool for their duration.** Pool sizing is now coupled to job duration and worker concurrency, and a batch of slow jobs can starve web request handlers if they share a pool. Worker and web pools should be sized and ideally separated with this in mind.

### Implications worth tracking (not decided here)

- Queue depth, oldest-ready-job age, and claim/completion rates need monitoring; the throughput ceiling is only a safe bet if we can see ourselves approaching it.
- Completed and failed job rows accumulate and need a retention policy, or the table's bloat becomes the performance problem before throughput does.
- The migration path off this design, if we ever need it, is to move consumers to a broker while keeping the table as an outbox — the enqueue-side code does not change. This is worth preserving as an option but is not planned work.

---

Two notes on what I'd tighten if you have the numbers: the headroom claim ("5–10x") is derived from your stated 40/s peak against "a few hundred per second," so if you have a measured ceiling from load testing, substitute it — a real number there makes the revisit trigger concrete. And if the 40/s peak is a burst rather than a sustained rate, saying so in the Context section changes how a future reader reads the ceiling.