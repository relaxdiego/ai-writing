Caching is likely the right instinct, but keying on the SQL string in a per-process dict has a failure mode that will bite you before the speedup does.

**The authorization leak.** If your queries use bound parameters — which they almost certainly do — then `SELECT * FROM orders WHERE user_id = ?` is a single cache key shared by every user on the system. User A's rows get served to user B. If you're interpolating user IDs directly into the SQL text you avoid this, but then you've got string-concatenated SQL, which is its own problem. Either way, any cache key for row-level-authorized data has to include the identity the authorization is scoped to, not just the query shape.

**Eight processes, eight caches.** A global dict lives in one process's memory. You'd have eight independent copies with no way to invalidate each other, so a write served by worker 3 leaves stale entries in workers 1, 2, 4–8. At 400 writes/min, staleness isn't a rare edge case — it's the normal condition. You'd need a shared cache (Redis, memcached) for invalidation to mean anything.

**Nothing ever evicts.** An unbounded dict keyed by SQL strings grows until the process dies. Parameterized queries collapse to a few hundred distinct keys, which is fine; anything that varies the SQL text (IN clauses with variable arity, dynamic filters) gives you unbounded key growth.

What I'd suggest instead:

1. **Measure first.** Pull slow-query logs or add per-endpoint query timing. Application slowness this often turns out to be N+1 query patterns or a missing index, and caching a query that should take 2ms instead of 400ms just hides the bug at the cost of correctness.

2. **If caching is still the answer**, use Redis with explicit, hand-written keys — `user:{id}:orders:v3`, not the SQL string — so you control the scope and can reason about who can see what. Short TTLs (30–60s) as a safety net, plus explicit invalidation on write.

3. **Cache selectively.** Reference data that rarely changes (config, product catalogs, permission lookups) is worth caching aggressively. Per-user data at 400 writes/min mostly isn't, unless you have a specific hot read path where you've measured the win.

4. **Check the boring stuff.** Connection pool sizing and missing indexes account for a lot of "the app is slow" cases and cost far less to fix than a cache layer.

If you can share the slow-query log or tell me which endpoints feel slow, I can help narrow down whether caching is even the lever worth pulling here.