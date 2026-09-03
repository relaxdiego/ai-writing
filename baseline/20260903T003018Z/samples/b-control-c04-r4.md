Short answer: **separate store — but a separate Postgres, not a different technology, and with a cold tier underneath it.** The split isn't "app DB vs. exotic append-only system," it's "hot audit vs. cold audit," and once you frame it that way most of your team's disagreement dissolves.

## The number that decides it

2M/day × 365 × 7 = **~5.1 billion rows**. At a conservative 400–800 bytes per event with indexes, that's **3–6 TB**.

Note what that number does *not* threaten: write throughput. 2M/day is ~23 inserts/sec average, maybe 200/sec at peak. Postgres will not blink. Anyone arguing "we need a specialized store because of volume" is solving the wrong problem.

What 5 TB *does* wreck is the operational profile of your application database. If your app data is, say, 200 GB, you've just made it a 5 TB database for every purpose that matters: base backup duration, PITR restore time, major-version upgrades, failover, replica rebuild, storage cost on provisioned SSD across primary + replicas + backups. Your RTO during an actual outage becomes dominated by seven years of records nobody is reading. That's the real cost, and it's the one that's hardest to unwind later.

## Why not a fully separate append-only store either

The two arguments your same-DB faction is making are both legitimate:

**The join.** But interrogate it. An audit event should snapshot the actor's identity, role, and relevant context *as of the event* — that's what makes it an audit record rather than a pointer to mutable state. If a user changes their email or gets deprovisioned, joining live `users` gives you a misleading answer in exactly the investigation where accuracy matters. Denormalize actor fields into the event. The residual need — "who is this user *today*" — is a support engineer running a second query, not a bulk join. Don't shape 5 TB of storage around an occasional convenience.

**Atomicity.** This one's real and underrated. Same-DB means the audit write commits with the action in one transaction. Split it and you can lose events, or log actions that rolled back. The fix is a **transactional outbox**: write the event to a small outbox table in the app DB inside the same transaction, a relay ships it to the audit store, rows are deleted on ack. The outbox stays tiny and transient. This is the honest price of splitting, and it's a few hundred lines, not a project.

## The shape I'd build

- **Hot tier:** dedicated Postgres instance, `audit` database, declarative **monthly partitions** from day one. Keep 12–18 months live — that's ~800M rows across ~15 partitions, entirely comfortable, and it covers the overwhelming majority of support investigations. Same SQL, same tooling, same on-call skills.
- **Cold tier:** roll partitions older than ~18 months out to **Parquet in S3 with Object Lock** (WORM). Query via Athena/DuckDB when legal or an auditor asks. Storage cost drops by roughly two orders of magnitude versus provisioned SSD.
- **Tamper evidence:** hash-chain each event (`prev_hash`), publish periodic checkpoint hashes somewhere independent. This is worth doing regardless of where the data lives, and it turns the auditor conversation from "we revoked DELETE from the app role" — which a superuser defeats — into a math argument. Revoking UPDATE/DELETE is still worth doing, it just isn't the proof.
- **Write path:** outbox as above.

Rough cost intuition: 5 TB on RDS gp3, plus a replica, plus backups, lands you north of $1.5k/month and growing monotonically for seven years. The cold-tier equivalent is tens of dollars. That delta funds the outbox work several times over in year one.

## The one decision you must not defer

If your team can't agree today, the fallback that preserves every option is: **put audit in its own database on the existing instance, partitioned monthly, with hash chaining, from the first row.** Partitioning is what makes a later move a partition-by-partition data migration instead of a rewrite. A single unpartitioned 5-billion-row audit table inside your application database is the only genuinely unrecoverable version of this decision.

## What would change my mind

- **A regulator or auditor explicitly requiring an independent WORM store from day one** — then skip the ambition of a long hot tier and dual-write immediately.
- **Analytics over audit data** (behavioral detection, anomaly scoring, wide aggregations) — ClickHouse becomes the better hot tier and the calculus shifts.
- **10x volume growth** — 20M/day changes this from "Postgres is fine" to "Postgres is a stretch."
- **No data-platform capacity at all** — a very small team might reasonably run the hot tier only and defer the S3 tier by a year. Acceptable, as long as partitioning and hash chaining are already in place.