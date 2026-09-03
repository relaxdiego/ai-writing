# ADR 0014: Use Postgres `SKIP LOCKED` for background job queueing

**Status:** Accepted. Implemented in Q3 2026, replacing the hand-rolled runner.

## Context

Background work currently runs through a job runner we wrote ourselves: rows in a table, a polling loop, and ad hoc handling of failure that has accumulated without design. It has no coherent retry policy, no scheduling, and no way to reason about a job that dies mid-execution. We want to replace it with something we can operate deliberately, and the choice of substrate determines both what we have to build and what we have to keep alive at three in the morning.

Our volume is modest and we expect it to stay that way for the foreseeable planning horizon. We process roughly 30,000 jobs a day with a measured peak of about 40 per second, concentrated around scheduled report generation. Nothing in the roadmap changes that by an order of magnitude.

Two constraints shaped the decision more than throughput did. The first is operational: we already run Postgres, with backups, monitoring, failover and on-call familiarity built around it. Adding Redis means adding a second stateful system to the on-call surface, with its own persistence semantics, its own failure modes, and its own page at two in the morning for an engineer who has never debugged it. The second is transactional. Most of our jobs are enqueued as part of a database write, and the job is only correct if it runs exactly when that write commits. A broker outside the database cannot give us this directly: enqueueing before commit produces jobs referencing rows that never existed, and enqueueing after commit drops jobs when the process dies in between. Closing that gap requires a transactional outbox, which means a table in Postgres, a relay process, and the operational weight of both, on top of the broker we were trying to get the queue from in the first place.

The team also has no Celery experience. This is not disqualifying on its own, but Celery's failure modes are subtle, and learning them under production pressure is a real cost that belongs in the comparison.

## Decision

We will implement job queueing in Postgres, using `SELECT ... FOR UPDATE SKIP LOCKED` against a jobs table to hand out work to concurrent workers without contention. Enqueueing happens inside the same transaction as the application writes that trigger it, so a job exists if and only if the work that justified it committed.

## Alternatives considered

Celery with Redis was the default expectation going in, and it is the most capable option: mature scheduling, a large operator community, and headroom far beyond our volume. It failed on the two constraints above. Redis enters the on-call surface, and Celery's at-least-once delivery from a separate broker still needs an outbox to be atomic with our writes. The team's unfamiliarity compounded both.

RQ is simpler than Celery and would have been easier to learn, but it carries the same Redis dependency and the same non-atomicity, while offering less than Celery in return. It removes the learning cost without removing either constraint that actually drove the decision.

## Consequences

We accept a throughput ceiling. Postgres-backed queueing degrades somewhere around a few hundred jobs per second, as polling and row locking begin to compete with application traffic for the same connections and buffers. At 40 per second peak we have roughly an order of magnitude of headroom, but the ceiling is real and we should treat sustained growth past 200 per second as the signal to revisit this record rather than tune around it.

We accept writing our own retry and scheduling logic, estimated at about 400 lines: exponential backoff with jitter, a dead-letter state, a heartbeat and reaper for jobs whose worker died holding a lock, and cron-style scheduling for recurring work. This is code Celery would have given us, and it is code we will own, test and debug ourselves. The estimate is small enough to be worth the operational simplicity, and large enough that we should not pretend it is free.

Long-running jobs hold a connection from the pool for their duration. This is the sharpest of the costs, because pool exhaustion presents as general application slowness rather than as a job system problem. We will run job workers against a separate connection pool from web traffic so that the failure is contained and legible, and we will set a maximum job duration with a hard timeout.

In exchange we get exactly-once enqueue semantics with no outbox, a single stateful system to operate, and a queue any engineer on the team can inspect with a `SELECT`.