Separate store — but the decision is less about the join and more about what seven years does to your application database.

Run the numbers: 2M/day × 365 × 7 is about 5.1 billion rows. At a few hundred bytes an event plus indexes you're looking at multiple terabytes sitting inside the database your application depends on. The write throughput is nothing (~25/sec average), so that's not the issue. The issue is that everything operational gets worse in proportion to size: base backups, restore time on your worst day, replica rebuilds, major-version upgrades, autovacuum behavior, and the blast radius of any storage incident. You'd be accepting permanent operational drag on your transactional system in exchange for the convenience of an occasional support query.

The compliance angle points the same direction. Auditors generally want evidence that audit records can't be modified after the fact. In a shared Postgres you can get most of the way there — dedicated role, `REVOKE UPDATE, DELETE`, append-only triggers — but any superuser or migration can undo it, and "we trust our DBAs" is a weaker story than object-lock/WORM on a separate system with its own credentials.

Now the join requirement, which I think is partly an anti-requirement. If a support investigation joins an audit event against the *current* user record, you get the wrong answer: you're reconstructing a past action using present-day state. Audit events should denormalize the relevant subject attributes at write time — user id, email, role, tenant, whatever mattered — so the record is self-contained and reflects the world as it was. Do that and most of your joins disappear. The residual "who is this user id now" lookups are cheap to satisfy by other means.

Concretely, what I'd build:

- Append-only audit table, range-partitioned by month, in a **separate database** (separate instance if budget allows, at minimum a separate logical database with its own role).
- Keep a hot window — 90 days to a year — in Postgres, where support actually lives. That's 180M–730M rows, entirely manageable with partition pruning.
- Age older partitions out to object storage as Parquet with object-lock for the compliance tail. Query them with DuckDB, Athena, or a foreign data wrapper when someone actually needs year five.
- Denormalize subject fields into every event so the hot table answers support questions without a cross-database join.

The one case for co-locating is if you need audit writes to be transactionally atomic with the business change — no event without the mutation, no mutation without the event. If that's a hard requirement, write to a local outbox table in the app database inside the same transaction and ship asynchronously to the audit store. You get the atomicity and still keep the seven-year archive out of your production database.