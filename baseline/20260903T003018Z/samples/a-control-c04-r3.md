## Recommendation

Separate store — but "separate" should mean a **separate Postgres database with time-partitioned tables, tiering to object storage**, not a different product. The team's split is probably a false binary: the append-only camp is right about the coupling risk, the same-database camp is right about the join, and you can have both.

## Why not the app database

At 2M events/day × 7 years you're at ~5.1 billion rows. At a realistic 500B–1KB per event that's 3–8 TB with indexes. Write throughput isn't the problem — 23/sec average, maybe a few hundred at peak, is nothing for Postgres. The problem is what that mass does to everything else:

- **Backup and restore become hostage to audit data.** If 90% of your cluster is audit rows, your application's recovery time objective is now determined by data nobody needs to restore the app. This is the single strongest argument and it's not really contestable.
- **Blast radius.** A runaway audit writer, a bad index build, an autovacuum storm on the audit table — all of it now contends with the transactions that serve users.
- **Retention mechanics.** Seven-year deletion on a heap table means either partitioning anyway or a permanent `DELETE`/vacuum treadmill.

## Why not a genuinely foreign store either

The recurring support-investigation join is real work, and cross-system joins turn a two-minute query into a ticket. Also worth pricing before anyone commits: 5B events in a SaaS log platform (Datadog, Splunk) over seven years is a large recurring cost for data you touch rarely. And immutability is not a property you have to buy — revoking `UPDATE`/`DELETE` from every role but a dedicated writer, plus rule/trigger guards, gets you append-only in Postgres today.

## The shape I'd build

1. **Separate Postgres instance** (or at minimum its own database + tablespace + roles), replicated and backed up on its own schedule. Physical separation, familiar tooling.
2. **Declarative monthly partitions.** Retention becomes `DETACH PARTITION`, which is instant.
3. **Hot window of 12–18 months online.** That's ~1B rows — fine with partition pruning and two or three deliberately chosen indexes. It also covers essentially every support investigation; nobody debugs a 2023 incident.
4. **Cold partitions exported to Parquet in S3 with Object Lock in compliance mode**, versioning on. Storage cost is tens of dollars a month at that volume. Query with Athena or DuckDB; keep a *tested* script that reloads a cold partition into Postgres when an investigation needs one.
5. **Denormalize the actor onto the event at write time** — `actor_id`, plus email, role, and org *as of the event*. This is the part I'd push hardest on regardless of which store wins. Joining audit events to the live `users` table gives you today's role and today's email, which is often the wrong answer for a compliance question and occasionally a misleading one for a support question. Self-contained events both eliminate most of the join need and are more correct. Keep the `actor_id` for the rare case you genuinely want current state; reach for `postgres_fdw` for that.
6. **If tamper-evidence is an actual requirement** and not just "append-only," add a hash chain: each row stores the hash of its content plus the previous row's hash. Cheap to write, and it detects modification by someone with superuser — which plain permissions cannot.

## What would change my mind

If the compliance regime names a specific control you can't demonstrate in Postgres — some regimes want the log outside the control of anyone who administers the audited system, which a hash chain only partially answers — then the cold tier becomes the system of record and the Postgres hot window becomes a queryable cache. Same architecture, different labeling, and it's worth confirming which one your auditor expects before you build.

If retention were one year instead of seven, I'd tell you to just put it in the app database and stop meeting about it. It's the seven-year figure that forces the tiering.