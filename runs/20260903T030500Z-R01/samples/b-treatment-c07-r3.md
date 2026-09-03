That plan has one failure mode that's a security bug, not a performance tradeoff, plus a few that will just quietly waste your time. Worth separating them.

**The dangerous one: what exactly is "the SQL string"?**

If your authorization lives in the WHERE clause and you use parameterized queries — `WHERE user_id = ? AND ...` — then the SQL string is *identical* for every user on the system. The thing that distinguishes Alice's rows from Bob's is the parameter, not the query text. Cache keyed on query text alone and the first user to run a query populates the entry, and every subsequent user gets Alice's rows back. That's a cross-tenant data leak served at cache speed.

If instead you interpolate values into the SQL before it's a string, the key happens to include the user ID and you're accidentally safe — but you're also caching per-user queries, so your hit rate collapses toward zero for exactly the queries that matter. The design is either unsafe or useless depending on a detail your framework picked for you.

Any cache key here has to include the full authorization context — user ID, role, tenant, whatever the WHERE clause reads.

**Eight processes means eight caches.** Each worker has its own dictionary, so a given user hits a cold cache roughly seven times out of eight, and your memory cost is 8× what you budgeted. More to the point, there's no way for a write in worker 3 to invalidate anything in worker 6. Which leads to:

**400 writes/min against a cache with no invalidation.** That's ~6.7 writes/second continuously making entries stale, with nothing to expire them. Users will see their own writes disappear on the next page load, non-deterministically depending on which worker the load balancer picks. That class of bug is miserable to reproduce and it'll show up as "the app is broken sometimes" long before anyone traces it to the cache.

**Unbounded growth.** A plain dictionary with no eviction is a memory leak with extra steps — every distinct query, forever, until the worker gets OOM-killed.

**What I'd suggest instead**

Start by finding out why it's slow, because caching is a fix for "the same expensive read happens repeatedly," and the usual culprit is something else. If you can get query timings out of your database's slow log or an APM tool, you'll typically find either a handful of queries missing an index, or an N+1 pattern where a loop fires one query per row. Both are cheap to fix and don't add a consistency problem to your system.

If there genuinely is a hot read path worth caching, the shape that works:

- **Shared cache** (Redis/Memcached) rather than per-process, so all eight workers see one state and invalidation is possible at all.
- **Explicit keys** at the application level — `user:{id}:dashboard:v2` — not the SQL string. You control what's in the key, so the authorization context is visible rather than implicit.
- **Short TTLs** as the safety net, plus explicit invalidation on write for anything users need read-after-write consistency on. TTL alone means every cached value is wrong for up to its lifetime.
- **Scoped narrowly** — cache the two or three reads that actually cost you, not everything.

Happy to look at the slow query log or the endpoint that's dragging if you want to point me at it — that'll tell us whether caching is the right tool here or whether an index does the job.