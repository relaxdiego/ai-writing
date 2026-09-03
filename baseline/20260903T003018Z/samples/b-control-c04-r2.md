## Where I'd land

Keep the write path in Postgres, but treat "Postgres" and "seven years of retention" as separate problems. Concretely: write audit events into the same database, in the same transaction as the change that produced them, into a time-partitioned table — then age partitions out to object storage with WORM/object-lock as the compliance archive.

That's not fence-sitting. It's saying the two options are being framed as one decision when they're actually two, and the right answer differs for each.

## Why the write path stays in Postgres

The strongest argument has nothing to do with joins or query convenience — it's that shipping to an external store makes audit writes a dual-write. Your transaction commits, the ship fails, and you've lost an audit event silently. Or the transaction rolls back after you've already shipped, and you've logged something that never happened. Both are exactly the failure mode compliance exists to prevent, and both are invisible until an auditor asks you to prove completeness.

Writing in the same transaction makes "the change happened" and "the audit event exists" the same fact. You can't get that from a separate store without an outbox, and an outbox is Postgres anyway.

The volume argument also doesn't favor separation as much as it feels like it should. 2M/day is ~25 writes/sec average, maybe 100/sec at peak. That's unremarkable for Postgres. The load isn't the problem.

## Why seven years doesn't stay in Postgres

Run the numbers: 2M × 365 × 7 ≈ **5.1 billion rows**. At ~500B–1KB per event that's 2.5–5 TB of heap, plus indexes on actor, target, timestamp, and event type — call it 5–10 TB realistically.

Postgres can hold that with partitioning. The problem is what it does to everything around it:

- Your application database backup and restore time is now dominated by data nobody queries. Restoring app data during an incident means dragging 5 TB of history along with it.
- You're paying OLTP-tier storage prices for cold archival data, forever.
- Extra WAL on the order of 4–6 GB/day flows through every replica and every backup.
- The "append-only" guarantee is weak. You can `REVOKE UPDATE, DELETE` and add a trigger that raises on modification, but a superuser or a migration bypasses it. That's a policy, not an immutability property.

Object storage with object lock gives you actual WORM semantics, and seven years of Parquet-compressed audit events is likely 300 GB–1 TB, costing something in the tens of dollars a month.

## The join requirement is weaker than it looks

"Occasionally join audit events against user records for support investigations" sounds like it forces colocation. It mostly doesn't:

1. These are point lookups, not analytical joins. You scope to one user or one time window — a few hundred rows — then enrich. That works fine across a boundary.
2. **Joining audit events to the live users table is arguably wrong.** An audit record should capture the actor's identity *as of the event*. If someone changed their email, changed roles, or was deleted, the live join gives you today's truth about a past event. You want actor email, role, and org denormalized into the event itself. Do that and most investigations need no join at all.

So denormalize the identity snapshot regardless of which architecture you pick. It makes the join question mostly evaporate.

## The concrete shape

- Range-partition by month on event time.
- Keep a hot window online — 12 to 18 months is ~700M–1.1B rows, comfortable when partitioned, and covers the overwhelming majority of support investigations with native SQL and native joins.
- Detach older partitions, export to Parquet in S3/GCS with object lock and versioning enabled.
- Query the cold tier with DuckDB or Athena on the rare occasion a five-year-old investigation comes up. "Rare investigations are slower and require a different tool" is an acceptable trade; "we lost audit events" is not.
- Add a `prev_hash` column and hash-chain the events. Periodically anchor the chain head into the WORM store. This costs almost nothing and gives you tamper-*evidence* even inside Postgres, which closes most of the gap the separate-store camp is worried about.

## What would flip me

**Multi-service audit sources.** If audit events originate in services that don't share the application database, there is no single transaction to preserve, and the dual-write argument disappears entirely. Then a log pipeline (Kafka → object store) is straightforwardly correct and I'd go that way. This is the question I'd resolve first — it matters more than anything else here.

**Volume 10–50× higher.** At 100M+/day, WAL and OLTP storage become the wrong tool regardless.

**An explicit regulatory requirement** for a separate attested WORM system. Some regimes do specify this; if yours does, it's not an architecture debate.

If the team really wants the external store as the system of record, the honest compromise is the transactional outbox: write to an outbox table in the same transaction, ship asynchronously with at-least-once delivery and idempotent consumers. That preserves correctness and reaches the external store. It's more moving parts than partition-and-detach for a similar outcome, but it's a defensible answer rather than a bad one.