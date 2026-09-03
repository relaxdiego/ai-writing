Caching is likely the right instinct, but this specific design has a correctness problem that outweighs the speed win, and two of your three constraints break it.

**The authorization bug is the serious one.** Your row-level auth lives in the WHERE clause, so the identity of the requesting user is part of what makes a result correct. If the SQL string is the key and the user ID arrives as a bound parameter — `WHERE owner_id = $1` — then every user's query hashes to the same key and you start serving user A's rows to user B. That's a data breach, not a bug report. Even with parameters folded into the key, any auth that comes from connection state rather than the query text (a `SET ROLE`, a session variable, a tenant set on the pooled connection) is invisible to the key and fails the same way. Interpolating the user ID directly into the SQL string happens to fix the key, but only because you've given up parameterization, which is its own problem.

**Eight processes means eight caches.** A global dictionary is per-process, so you get eight independent copies with no coordination. A user who writes through worker 3 and reads through worker 6 sees their own change disappear. Read-your-own-writes violations are the class of bug that generates support tickets nobody can reproduce.

**400 writes/min is enough to make staleness constant.** That's a write every 150ms, so at any moment some meaningful fraction of your cache is wrong. Without invalidation the cache is just a stale-data generator, and invalidation is the hard part — you'd need to map each write to every cached query whose result it could change, and broadcast that to seven other processes.

Two smaller ones: an unbounded dictionary keyed by SQL strings never evicts, so it's a slow memory leak, and it will happily cache queries containing `NOW()`, `RANDOM()`, or anything inside an open transaction.

**What I'd suggest instead**

Start by finding out where the time actually goes. Turn on slow-query logging or `pg_stat_statements` for a day. Application slowness this often turns out to be a missing index, an N+1 loop issuing 200 queries per page, or connection pool exhaustion — none of which caching fixes, and all of which are cheaper to fix than a cache is to operate.

If caching is genuinely the answer after that, the shape that works here is:

- **Shared store, not per-process** — Redis or memcached, so all eight workers see one cache and one invalidation.
- **Identity in the key** — key on `(query, all parameters, user or tenant ID)`, never the SQL text alone. Better still, cache at a layer above SQL, where the authorization scope is explicit rather than buried in a WHERE clause.
- **Short TTLs plus explicit invalidation on write** — TTL as the safety net, invalidation as the mechanism.
- **Only the queries that earn it** — expensive, read-heavy, tolerant of being a few seconds stale. A per-user dashboard aggregate is a good candidate; the query that checks whether the current user may view a record is not.

If you can tell me what the slow endpoints are, or paste a slow-query log sample, I can point at which of these applies.