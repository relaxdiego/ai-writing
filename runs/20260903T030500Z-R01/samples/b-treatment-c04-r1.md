Same Postgres, but partitioned and tiered — not "one big audit table forever," and not a separate store from day one.

**Why same database**

The strongest argument is transactional integrity. If the audit write is in the same transaction as the mutation it describes, it's impossible to have a recorded change with no event, or an event for a change that rolled back. Ship to a separate store and you're dual-writing, which means picking which of those two failure modes you'd rather explain to an auditor. That's a real correctness property you'd be trading away, and it's usually worth more than what you get back.

Second, you named joins against user records as a live requirement. In-database that's a query; cross-store it's an export-and-reconcile job that someone has to maintain and that goes stale.

**Why append-only isn't the reason to leave**

Separate stores get credited with tamper-evidence they don't actually provide — if your app can write to it, your app can write garbage to it. You get the same property in Postgres by giving the writer role `INSERT` only, revoking `UPDATE`/`DELETE`, and putting the table in its own schema. Add hash chaining per row if your compliance regime wants provable ordering.

**Why tiering is non-negotiable**

2M/day × 7 years is ~5 billion rows. At 500B–1KB per event that's 2.5–5 TB before indexes, sitting on the primary that also serves application traffic — dragging backup windows, restore time, and vacuum behavior for data that is almost never read.

So: declarative partitioning by month (84 partitions, well within what Postgres handles comfortably). Keep a hot window online — 12 months is a reasonable starting point, tune from actual support-investigation lookback. Detach older partitions, write them to object storage as Parquet with object lock for WORM, keep a checksum manifest. Cold reads become a DuckDB or Athena query, which is fine for the rare seven-year-old investigation.

Two things to get right early: index discipline (audit tables attract indexes; you likely need `(actor_id, occurred_at)` and `(entity_id, occurred_at)` and little else, since every index is paid 2M times a day), and building the detach-and-archive job before you need it rather than at 3 TB.

**When I'd flip**

Go straight to a separate store if your compliance regime explicitly requires independent custody — audit data the application operators cannot reach — or if the events are unstructured blobs with unpredictable query shapes, where a log-oriented store genuinely fits better than a relational one. Neither appears to be the case from what you've described.