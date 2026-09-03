Go with a **separate Postgres instance, not a separate technology** — and treat "same database" and "different store" as the wrong axis for the decision.

Here's the reasoning.

## The numbers first

2M/day is ~23 events/sec average, maybe 150–300/sec at peak. That is nothing for Postgres write throughput. Volume is not your problem.

Seven years is your problem: ~5.1 billion rows. At a realistic 400–800 bytes per event plus indexes, you're looking at 4–8 TB. That's not "Postgres can't do it" territory — it's "this now dominates every operational property of the database it lives in" territory. Your backups, your restore-time RPO, your major-version upgrade window, your vacuum behavior, your replica seeding, and your storage bill all become functions of the audit log rather than of your application. A 30-minute restore becomes a 6-hour one because 95% of the bytes are records nobody has read in three years.

So: same engine, own cluster, own lifecycle.

## Why not a genuinely separate append-only store

The strongest argument for keeping audit in Postgres is atomicity. If the audit write is in the same transaction as the state change, you cannot get a change without its audit record, or an audit record for a change that rolled back. The moment you ship to an external store, you're dual-writing, and dual writes fail independently. Fixing that properly means a transactional outbox — write the event to a local Postgres table in the same transaction, relay it asynchronously — which means you're running Postgres for audit events *anyway*, plus a relay, plus a second store, plus reconciliation to prove the relay didn't drop anything.

"Audit log is missing events" is a compliance finding. Buying that risk to get a purpose-built store is a bad trade unless something else forces it.

## Getting the append-only property without leaving Postgres

Auditors generally want three things, and you can supply all three:

- **Application credentials cannot mutate history.** Separate role; `GRANT INSERT, SELECT` and no `UPDATE`/`DELETE` on the audit tables. The app's connection literally lacks the privilege.
- **Tamper evidence.** Hash-chain the rows — each event carries a hash over its own content plus the previous event's hash, sealed per partition. Any retroactive edit breaks the chain and is detectable. Publish periodic chain checkpoints somewhere out of reach of a DBA.
- **Enforced retention.** Covered by the tiering below, with real WORM at the storage layer.

That's stronger than most "append-only stores" give you out of the box, because most of them are append-only by convention and IAM policy too.

## The shape I'd actually build

Partition by month (`RANGE` on `occurred_at`). Then tier:

| Tier | Where | Span | Purpose |
|---|---|---|---|
| Hot | Audit Postgres cluster | 12–18 months | Support investigations, joins, ad-hoc queries |
| Cold | Parquet in object storage, Object Lock in compliance mode, 7-year retention | everything older | Retention obligation, occasional forensics |

Hot stays around 350–550M rows, which Postgres handles comfortably with sane indexes. Sealed partitions get exported, checksummed, verified against the hash chain, then detached and dropped. Object Lock in compliance mode gives you WORM that even your own root credentials can't override — which is the thing you were actually shopping for when someone said "append-only store." Compressed Parquet will also land somewhere near 400–800 GB for the full seven years instead of multiple TB of replicated SSD. Query it with DuckDB or Athena on the rare occasions you need it.

## The join requirement

Two things here, and the second one matters more than the first.

For the mechanics: replicate the `users` table into the audit cluster via logical replication. It's small, it's cheap, and it makes joins local and fast. Don't reach for `postgres_fdw` — cross-server join pushdown is unreliable and you'll get a 5-billion-row scan shipped across the wire the first time someone writes a query slightly wrong.

But the more important point: **you should not be depending on those joins for correctness.** Denormalize the actor's identity into the event at write time — `actor_id`, plus email, display name, role, and tenant *as they were at that moment*. A 2027 support investigation into a 2021 event does not want the user's current role; it wants the role they held when they did the thing. And users get renamed, deprovisioned, merged, and GDPR-erased, so the join may not even resolve. Once identity is snapshotted, the live join becomes an enrichment convenience ("who is this person *now*") rather than the only way to interpret the record — which substantially weakens the case for co-location that started this debate.

Related: no foreign keys from audit events to application tables. That's coupling you'll regret at deletion time.

## What would change my answer

- A regulator or customer contract that names an external immutable ledger or a specific SIEM as the system of record. Then ship there — but keep the outbox in Postgres and reconcile counts, so a broken pipeline is loud rather than silent.
- These events are really security telemetry that SecOps wants alerting on. Then it's not an audit log, it's an event stream, and it belongs in whatever they already run — with the compliance-grade copy still landing in the archive above.
- Audit volume is projected to grow 10–50×. At 100M/day the arithmetic changes and a columnar store earns its complexity.

**Summary:** own Postgres cluster, monthly partitions, insert-only role, hash-chained rows, users table logically replicated in for joins, sealed partitions exported to WORM object storage after 12–18 months. You keep transactional atomicity and SQL joins, you stop the audit log from dictating your application database's operational envelope, and the seven-year obligation gets satisfied by storage that's built for it.