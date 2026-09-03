Keep it in Postgres — same cluster, separate schema, partitioned by month, with old partitions detached to object storage. Don't stand up a second system.

**Why the volume doesn't justify separation.** 2M events/day is ~23 writes/sec average, maybe a few hundred at peak. That's unremarkable for Postgres. The real number is 5.1 billion rows over seven years, roughly 2–5 TB depending on payload size. That's too much to leave sitting in your primary's backup set, but it's a partitioning problem, not an architecture problem.

**Why the join requirement is smaller than it looks.** Support investigations are almost always about recent activity — days or weeks, occasionally months. Nobody joins a 2023 audit event against a live user record to resolve a ticket. So the window that needs joinability and the window that needs seven-year retention barely overlap. Splitting by *age* rather than by *system* gets you both.

Also, don't foreign-key audit events to `users`. Snapshot the actor identity into the event itself — user ID, email, role, and whatever else mattered at the time of the action. Audit records have to stay accurate after the user is renamed, demoted, or deleted, and auditors specifically want the state as of the event. Once you do that, the join is enrichment rather than correctness, which lowers the stakes further.

**What I'd actually build:**

- Audit tables in their own schema, monthly `PARTITION BY RANGE` on event time.
- Append-only enforced by grants: the app role gets `INSERT` and `SELECT`, no `UPDATE`/`DELETE`. Add a `BEFORE UPDATE OR DELETE` trigger that raises, as a second layer.
- Keep ~90 days hot (roughly 180M rows). Detach older partitions and write them to S3 as Parquet, with a manifest. Query them with DuckDB or Athena when legal or compliance asks — which is rare and doesn't need to be fast.
- Hash-chain the events (each row stores a hash of its contents plus the prior row's hash) if tamper-evidence is a real compliance requirement.

That last point is worth surfacing with your team, because it's often the unspoken reason people want a separate store. A different database doesn't make your log immutable — anyone with admin credentials can still rewrite it. Immutability comes from the chain and from shipping periodic checkpoint hashes somewhere you don't control. If that's the actual requirement, moving the data doesn't satisfy it and hash-chaining does.

**What would change my answer:** if audit writes have to survive the application database being down or corrupted — i.e. the log is a control on the system it lives inside — then co-location is a genuine problem and you want a separate write path. Ask your compliance people whether that's in scope. If it isn't, a second datastore is operational cost with no return.