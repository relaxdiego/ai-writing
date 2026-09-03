I'd separate it — but probably not in the way either side of your team is arguing, and the write path should still start in Postgres.

## The numbers first

2M events/day is ~23 writes/sec average, maybe 150–300/sec at peak. That is nothing for Postgres. Write throughput is not your problem and shouldn't be part of the argument.

The problem is cumulative size. 2M × 365 × 7 ≈ **5.1 billion rows**. At a realistic 400–800 bytes per event (actor, target, action, timestamp, IP, plus a JSONB payload), that's 2–4 TB of heap before indexes, call it 4–7 TB with them. Your application data is probably a fraction of that.

That ratio is the real argument, and it isn't about query performance — a monthly-partitioned table with 84 partitions handles reads fine. It's about **operational coupling**:

- Base backups and PITR restore windows are now driven by audit volume, not app volume. Your RTO for the thing that actually matters (the app) gets held hostage by the thing that doesn't (7-year-old audit rows).
- Major version upgrades. `pg_upgrade --link` helps, but logical replication cutovers and any full rebuild get 10x harder.
- Every read replica, every staging clone, every dev-environment restore carries 5 TB of compliance data it has no business holding.
- Autovacuum, bloat, and freeze storms on billion-row tables become an app-availability concern.

You'd be letting a write-once, read-almost-never dataset set the operational tempo for your transactional database. That's the wrong tail wagging the dog.

## But don't decouple the write

The thing the "same database" camp is right about: for most compliance regimes, **an action and its audit record must be atomic**. If you fire an event at Kafka or an HTTP audit service and it fails, you either drop the record or you fail a user action that already succeeded. Both are bad, and "we'll retry in a queue" is exactly the gap an auditor will find.

So: write the audit event into the application database, in the same transaction as the action it describes, into a short-retention table (30–90 days). Then ship it asynchronously to the long-term store — outbox pattern, logical replication, or a simple watermark-based drainer. You get transactional integrity where it matters and you cap the size of the thing living in your app DB.

## Make the long-term store Postgres too

This is where I'd push back on "separate append-only store" if it means Kafka, Elasticsearch, or a bespoke service. Pick a **separate Postgres instance** on its own storage, monthly-partitioned, with:

- A dedicated role that has `INSERT` and `SELECT` only — `REVOKE UPDATE, DELETE` on the audit schema. That's most of "append-only" for 90% of compliance conversations.
- A hash chain (each row stores `hash(prev_hash || payload)`) if you need tamper-evidence rather than just tamper-resistance. Cheap to add now, impossible to backfill later.
- Cold partitions older than ~18 months detached and exported to Parquet on object storage with a lock/retention policy. That's your actual 7-year archive; query it with DuckDB or Athena when someone asks.

Keeping it Postgres means your team already knows how to operate it, and it preserves the thing you said you care about.

## The joins

Here's the part people over-weight. For support investigations you almost never need a live join against current user records — you need to know **who the user was at the time of the event**. Denormalize it: store `actor_id`, `actor_email`, `actor_role`, `org_id` on the event itself. That's correct for audit purposes anyway (a role change three years ago shouldn't retroactively rewrite what a 2023 log entry means) and it makes the majority of investigations single-table lookups.

For the residual cases where you genuinely need current app state, you have two easy options: `postgres_fdw` from the audit instance back to a read replica of the app DB, or logically replicate the small `users`/`orgs` dimension tables *into* the audit instance. The second is better — it keeps queries local and works even if the app DB is down.

## What would change my answer

- **Under ~200k events/day** (so <500 GB at 7 years): keep it in the app DB, partitioned. Not worth the second system.
- **A regulator that names WORM storage explicitly** (SEC 17a-4, some healthcare regimes): you need object-lock immutable storage as the system of record from day one, not as an archive tier. Design backward from that.
- **Audit reads that are analytical rather than point lookups** — dashboards, aggregations, anomaly detection over months of data: then a columnar store (ClickHouse) earns its keep and the calculus shifts.

Short version: same database for the *write*, separate Postgres for the *retention*, denormalized actor fields so joins mostly disappear, object storage for the cold tail.