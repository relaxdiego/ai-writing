# Replace the hand-rolled job runner with Postgres `SKIP LOCKED` queueing

Status: Accepted. Implemented in Q3 2026.

## Context

Our background work currently runs through a job runner we wrote ourselves, which polls a table, marks rows in flight with an advisory update, and relies on a single worker process to avoid double execution. It has served us, but it has no retry semantics worth the name, no scheduling, and no story for running more than one worker safely. We want to replace it with something we can reason about, and the choice of queueing substrate determines most of what follows.

The workload is modest and well understood. We process roughly 30,000 jobs a day, with observed peaks around 40 per second during the morning import window. Growth has been steady rather than sharp, and nothing in the roadmap suggests an order-of-magnitude change in job volume within the horizon this decision needs to cover.

Two properties of the workload matter more than throughput. The first is atomicity: most jobs are enqueued as part of a database transaction that also writes application state, and the job must not become visible to a worker if that transaction rolls back, nor be lost if it commits. The second is operational surface. We run Postgres already, we have backups, monitoring, failover and on-call familiarity for it, and every additional stateful system we introduce is a new thing that pages someone at three in the morning.

## Decision

We will implement job queueing directly in Postgres, using `SELECT ... FOR UPDATE SKIP LOCKED` to hand distinct rows to concurrent workers, and we will write the retry, backoff and scheduling logic ourselves on top of that primitive.

## Alternatives considered

Celery with Redis is the default answer in our ecosystem and would give us retries, scheduling via beat, and a large body of documentation for free. It fails on the two properties above. Enqueueing to Redis inside a Postgres transaction gives us no atomicity, so correctness would require a transactional outbox table plus a relay process, which reintroduces the Postgres-backed queue we were trying to avoid and adds Redis alongside it. Redis also becomes a second stateful system on the on-call rotation, with its own persistence configuration and failure modes. Against that, nobody on the team has run Celery in production, and its configuration surface, prefetch behaviour and result-backend semantics are a well-known source of subtle production surprises for teams learning it under load.

RQ is considerably simpler than Celery and would have been a reasonable choice on ergonomics alone. It still requires Redis, so it inherits the atomicity gap and the extra operational surface without solving either. Its scheduling support is thinner than Celery's, which narrows the advantage it would have bought us over writing our own.

Postgres with `SKIP LOCKED` gives us exactly the atomicity we need, because the enqueue is an ordinary `INSERT` in the same transaction as the application writes. Workers claim rows without blocking each other, visibility follows normal transaction semantics, and inspecting or repairing the queue is a `SELECT` in a tool everyone on the team already uses. The cost is that we build the parts Celery would have given us.

## Consequences

We accept a throughput ceiling. Row-level locking with polling workers is generally sound into the low hundreds of jobs per second, above which lock contention, table bloat from high-churn updates and vacuum pressure start to dominate. That is roughly an order of magnitude above our current peak, which gives us room but not indefinite room. If sustained volume approaches 200 jobs per second we should treat that as the trigger to revisit this decision rather than tuning our way past it.

We take on roughly 400 lines of retry and scheduling logic that we now own and must test: exponential backoff with jitter, a maximum attempt count, a dead-letter disposition for exhausted jobs, and a `run_after` column for delayed and periodic work. This code is not conceptually hard, but it is code that a library would have carried, and it will need maintenance and its own test suite.

Long-running jobs hold a pooled connection for their duration, since the claim is held by an open transaction. This couples job concurrency to connection capacity, so worker pool sizing must be considered against the application's connection budget, and jobs that block on slow external calls are disproportionately expensive. We should keep a separate connection pool for workers so that a backlog of slow jobs cannot starve request-serving traffic, and we should set a statement timeout on the worker pool to bound the damage from a wedged job.

Queue tables are high-churn and will need attention to autovacuum settings, and completed jobs should be moved to an archive table or deleted on a schedule rather than accumulating in the hot table. Monitoring should track queue depth, oldest unclaimed job age, and attempt-count distribution, since these are the signals that will tell us whether the throughput assumption still holds.