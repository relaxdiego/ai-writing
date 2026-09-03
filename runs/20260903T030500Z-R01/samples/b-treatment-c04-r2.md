I'd split the difference, but not the way the debate is usually framed: same engine, separate database — with tiering.

The join requirement is real and it's what kills the "ship it all to an append-only store elsewhere" option. Cross-store joins during a support investigation mean someone exports a CSV, or you build a query service nobody maintains. But that requirement only applies to *recent* audit events. Nobody joins a 2019 event against a user record to answer a support ticket.

The argument against the same database is not "Postgres can't do append-only" — it can. Revoke UPDATE and DELETE from the app role, write through an insert-only role, done. The argument is operational coupling. Seven years at 2M/day is ~5 billion rows, likely 3–6 TB with indexes. That number lands in your application database's backup size, restore time, WAL volume, vacuum pressure, and connection pool. You will eventually want to restore the app DB quickly during an incident and discover you're waiting on audit data from 2021.

So:

- **Hot tier (0–12 months, ~700M rows):** a separate Postgres instance or database, partitioned monthly by event time. Reachable for joins via postgres_fdw, or by replicating the user table into it — the user dimension is small and slow-moving, so a logical replication subscription is cheap and makes joins local.
- **Cold tier (1–7 years):** monthly partitions exported to Parquet in object storage with versioning and object lock, detached and dropped from Postgres. Queryable by DuckDB or Athena when compliance or legal asks. Retrieval latency of minutes is fine for that audience.

Two things worth checking before committing.

First, what your compliance regime actually says about immutability. If it demands tamper-evident or WORM storage (common under SOX, and some interpretations of HIPAA), "we revoked DELETE from the app role" is a weaker story to an auditor than S3 Object Lock in compliance mode. If that's the requirement, the cold tier stops being an optimization and becomes the point, and you should add hash chaining — each event carrying a hash of its predecessor — so gaps are detectable.

Second, whether 2M/day is stable. At that rate a single insert-only Postgres instance is comfortable, roughly 25 writes/second average. If it's growing 3× a year, revisit; if it's flat, this design will hold for the full seven years without further thought.

The version of this I'd argue against is putting everything in the app database and planning to "deal with retention later." Seven years of coupling accrues quietly and is expensive to unwind once the table is 4 TB.