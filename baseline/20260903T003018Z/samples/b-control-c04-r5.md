## Short answer

Separate store — but the decision is less binary than the debate probably feels, and the reason to separate is not the one usually argued.

## The number that decides it

2M/day × 365 × 7 = **~5.1 billion rows**. At a realistic 300B–1KB per event (actor, action, resource, timestamp, JSONB context), that's **1.5–5 TB of data before indexes**, call it 3–8 TB with them.

Note what that number *doesn't* say. The write rate is ~23/sec average, maybe 200/sec at peak — Postgres won't notice. Query volume for support investigations is a handful per day. Neither throughput nor query load is the problem, and if your team is arguing about those, they're arguing about the wrong thing.

The problem is that you'd be attaching 3–8 TB of write-once data to the database whose restore time, failover window, backup cost, and upgrade risk govern whether your product is up. Your audit log's RPO/RTO requirements are wildly different from your application's — audit can tolerate hours of lag and needs to survive a decade; app data needs sub-minute recovery and lives in a working set measured in gigabytes. Coupling them means the strictest requirement on each axis wins, and you pay for both forever. A `pg_restore` that used to take 20 minutes now takes most of a day, during an outage.

The secondary reason is authorization. "Append-only" is a property you enforce with grants and physical separation, not with intent. If the audit table lives in the database your application connects to, the application's role can `UPDATE` and `DELETE` it, and every future migration script is one `WHERE` clause away from an unprovable audit trail. When an auditor asks "how do you know these records weren't modified?", "our developers agreed not to" is not an answer.

## Three decisions the debate is conflating

It helps to split the question:

1. **Same technology?** Probably yes — a second Postgres is fine. You don't need Kafka or a specialty ledger DB for 23 events/sec.
2. **Same instance?** No, for the reasons above.
3. **Same transaction?** *Yes* — and this is the part the "separate store" camp usually gets wrong.

That third one is the real argument for co-location, and it's a good one: if the audit write is a separate network call, then crashes, timeouts, and partial failures produce mutations with no corresponding audit event. Silent gaps in an audit log are worse than a slow audit log.

You get both with the **outbox pattern**: write the audit event to a small local table inside the same transaction as the mutation, and have a shipper drain it to the audit store asynchronously. Atomicity preserved, storage decoupled, outbox stays tiny because rows are deleted after shipping.

## On the joins

Denormalize the identity fields into the event at write time — user ID, email, display name, role, tenant, as they were *at the moment of the action*. You want this regardless of where the data lives: an audit record that says "user 4417 deleted the account" and requires a join to a mutable `users` table to interpret is not really an audit record, and it will lie to you the moment someone changes their email or gets deleted.

That kills most join needs outright. For the residual cases, a foreign data wrapper (`postgres_fdw`) from the audit DB back to app Postgres handles ad-hoc support queries at a few-per-day cadence perfectly well.

## Concrete shape

Separate Postgres instance; `INSERT`-only grant for the writer role, no `UPDATE`/`DELETE` for anyone but a break-glass admin; declarative partitioning by month (84 partitions, ~60M rows each — comfortable); partitions older than 12–18 months detached and exported to Parquet in object storage with lifecycle policies. Seven years of cold audit data in S3 is tens of dollars a month; seven years of it in your primary's storage and every backup snapshot is not.

## What would change my answer

If the 7-year retention is being driven by a regulator that requires *demonstrable* immutability (SOX, some healthcare and financial regimes), then grants aren't sufficient and you want hash-chained records or genuine WORM storage — S3 Object Lock in compliance mode. That's worth confirming before you build, because retrofitting tamper-evidence onto 5 billion existing rows is not fun. If it's an internal policy rather than an external auditor, the plain separated-Postgres version is enough.