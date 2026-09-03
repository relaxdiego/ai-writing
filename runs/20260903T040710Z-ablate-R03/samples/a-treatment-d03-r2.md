# Background job queueing on Postgres with `SELECT ... FOR UPDATE SKIP LOCKED`

**Status:** Accepted; implemented in Q3.

## Context

Background work currently runs through a hand-rolled runner that polls a table, marks rows in place, and offers no retry policy, no scheduling, and no protection against two workers picking up the same job. It has survived on low volume and careful deploys, and we are replacing it before it fails in a way that costs us data rather than a page.

Four things shaped the choice. We already run Postgres in production and have the operational habits for it, and adding Redis would put a second stateful system on the on-call surface, with its own failure modes, its own persistence configuration, and its own upgrade path. Our volume is modest: roughly 30,000 jobs a day, which averages well under one per second, with observed peaks around 40 per second. Most of our jobs are enqueued as a consequence of a database write and must commit or roll back with it, so that a rolled-back transaction leaves no job behind and a committed one leaves exactly one. Finally, nobody on the team has run Celery in production.

We evaluated Celery with Redis, RQ, and a queue table in Postgres drained with `SKIP LOCKED`. Celery is the most capable of the three and the most operationally expensive: it brings a broker, a result backend, a worker model with prefork semantics we would have to learn under load, and a configuration surface that rewards experience we do not have. RQ is a much smaller system and easier to reason about, but it still requires Redis, which is the cost we were most trying to avoid. Both are separate brokers, so neither can enqueue a job inside the transaction that produced it; getting atomicity back means writing a transactional outbox table and a relay process, at which point we are running the Postgres queue anyway plus a broker on top of it.

## Decision

Jobs are rows in a Postgres table. Producers insert them in the same transaction as the domain writes that motivate them, so enqueue is atomic with the state change and no outbox is required. Workers claim jobs with `SELECT ... FROM jobs WHERE ... ORDER BY run_at FOR UPDATE SKIP LOCKED LIMIT n`, which lets concurrent workers pass over each other's locked rows instead of serialising behind them, and they hold the claiming transaction for the life of the job so that a crashed worker releases its lock on disconnect.

Retry, backoff, delayed execution, reclaiming jobs abandoned by dead workers, and dead-lettering are ours to write, budgeted at roughly 400 lines against the alternative of learning and operating a framework that supplies them.

## Consequences

The practical ceiling for this design is somewhere in the low hundreds of jobs per second, above which lock contention and table churn on the queue make it the wrong tool. Our peak sits near a tenth of that, so the headroom is real but finite, and it is the number to watch: sustained peaks above roughly 150 per second, or queue-table vacuum and bloat showing up in Postgres monitoring, are the signals to revisit this record rather than tune around it.

We own the retry and scheduling code, which means bugs in it are ours to find and no upstream release will fix them. In exchange, the semantics are legible in our own repository, and the failure modes are ones we can read rather than infer from a framework's documentation.

Long-running jobs hold a pooled connection for their full duration, so worker concurrency and pool size are now coupled in a way they were not before. Workers should draw from a pool sized separately from the one serving web requests, so that a burst of slow jobs degrades background throughput instead of starving the application.