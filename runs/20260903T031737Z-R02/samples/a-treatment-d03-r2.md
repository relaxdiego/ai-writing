# ADR-0007: Use Postgres `SKIP LOCKED` for background job queueing

**Status:** Accepted. Implemented in Q3.

## Context

We are retiring the background job runner we wrote in-house and moving to a real queue. The question this record settles is not whether to adopt a queue but which substrate to run it on, since that choice determines what we operate, what we page on, and what guarantees we can offer callers who enqueue work.

Our volume is modest and we expect it to stay that way for the foreseeable planning horizon. We process roughly 30,000 jobs a day, which averages well under one job per second, with observed peaks around 40 per second. The peaks are what any candidate has to absorb, and they sit about two orders of magnitude below the throughput at which the usual queue-scaling arguments start to bite. Choosing for a load profile we do not have would mean paying real operational cost now against a scaling problem that may never arrive.

The requirement that did the most work in this decision is atomicity. Most of our jobs are enqueued from inside a transaction that is also writing to the database — a row is created, and a job must run against that row. With a broker outside the database, the enqueue and the write cannot commit together, so we would have to choose between a job that fires against a row that was rolled back and a row that commits with no job to process it. The standard fix is a transactional outbox, which means a table, a relay process, and a second delivery path to keep correct. If we are going to run a durable table of pending work inside Postgres anyway, the outbox is most of a queue already, and adding a broker behind it buys throughput we do not need at the price of a component we would then have to keep in sync.

Two further constraints narrowed the field. We already run Postgres with backups, monitoring, failover, and on-call familiarity, whereas Redis would be a new stateful service on the on-call surface with its own persistence and eviction semantics to reason about at three in the morning. And nobody on the team has operated Celery. Its configuration surface, worker model, and failure modes are learnable, but the learning would happen in production during an incident, and that cost lands on the same small group carrying the pager.

## Alternatives considered

**Celery with Redis** is the most capable option and the most expensive one for us. It brings scheduling, retries, chains, and routing that we would otherwise write, and it scales far past anything we project. Against that, it adds Redis to the services we operate, it cannot commit jobs atomically with our database writes without an outbox, and it asks a team with no Celery experience to take on a large and opinionated framework. The capabilities we would be buying are mostly ones our workload does not exercise.

**RQ** is a much smaller framework and a genuinely reasonable middle option; it is simple enough to read end to end and would take days rather than weeks to learn. It still requires Redis, however, so it carries the operational cost and the atomicity gap without resolving either. Since the Redis dependency was the dominant cost in the Celery evaluation, RQ inherits the decisive objection while offering less in return.

**Postgres with `SELECT ... FOR UPDATE SKIP LOCKED`** adds no new infrastructure, makes enqueue a plain insert that commits with the surrounding transaction, and gives us jobs we can inspect, count, and correct with ordinary SQL. The cost is that we write the parts a framework would have supplied.

## Decision

We will implement job queueing as a Postgres table consumed with `SELECT ... FOR UPDATE SKIP LOCKED`. Enqueue is an insert on the same connection and transaction as the caller's writes, so a job exists exactly when the work it refers to has committed. Workers claim batches by locking rows with `SKIP LOCKED`, which lets concurrent workers pull disjoint work without blocking on each other.

## Consequences

We accept a throughput ceiling in the range of a few hundred jobs per second. This is roughly an order of magnitude above our current peak, so it is headroom rather than a constraint today, but it is a real limit and it is closer than any broker's would be. Growth in job volume is therefore something we need to watch rather than assume away.

We accept that we own the retry, backoff, and scheduling logic — on the order of 400 lines, by our estimate during design. Code we write is code we maintain and test, and we will not get the ecosystem of a mature framework for free. In exchange the semantics are ours to read and change, which matters more than usual given that the alternative was a framework nobody here has debugged.

We accept that a running job holds a connection from the pool for its duration, which makes long jobs a source of pool pressure and couples worker concurrency to connection budget. Workers should draw from a pool sized separately from the application's, and job handlers that run for minutes rather than seconds should be treated as a design smell to be broken up rather than accommodated.

We should revisit this decision if sustained throughput approaches a hundred jobs per second, if queue polling becomes a measurable share of database load, or if the retry and scheduling code grows substantially beyond its initial size. Any of those would mean the tradeoff we made here has stopped holding, and the case for a dedicated broker — with an outbox for the transactional path — should be re-argued on the numbers at that time.