I'd push back on this one — not on caching generally, but on this specific design. Three of the details you mentioned turn it from a speedup into a bug source.

**1. Keying on the SQL string leaks data across users.**

Your authorization lives in the WHERE clause. If you're using parameterized queries (you should be), the SQL string is identical for every user:

```sql
SELECT * FROM documents WHERE owner_id = ? AND archived = false
```

User A runs it, populates the cache. User B runs it, gets a key hit, and receives **user A's rows**. That's a cross-tenant data disclosure, and it's the kind that doesn't show up in testing because your test users usually run queries in a predictable order.

The alternative — interpolating parameters into the key — avoids the leak but destroys the hit rate. A key of `...WHERE owner_id = 8814...` is unique per user, so you get roughly one cache entry per user per query shape and almost no reuse. You'd be paying memory and complexity costs for very little.

Either way, the SQL string is the wrong key. Any cache key here has to explicitly include the authorization scope (user/tenant ID), which means it can't be derived from the query text alone.

**2. Eight worker processes means eight caches.**

A global dictionary is global *within one process*. With eight workers behind a load balancer you get eight independent caches with eight times the memory footprint and roughly one-eighth the hit rate each — every worker has to miss once on its own before it warms.

Worse, the caches disagree. A user's request goes to worker 3, they update something, their next request lands on worker 6 which serves a stale value. Users experience this as "I saved it and it didn't save," then they hit refresh and it's back. It's a genuinely miserable class of bug to debug, because reproducing it depends on which worker you land on.

**3. 400 writes/minute means the cache is wrong most of the time.**

That's ~7 writes per second continuously invalidating cached reads. Without an invalidation strategy the dictionary just accumulates stale data — and a plain dict has no TTL and no eviction, so it also grows without bound until the worker gets OOM-killed. Long-running workers with unbounded dicts are one of the more common causes of "the app gets slower over the day and then restarts."

---

**What I'd suggest instead**

First, find out where the time actually goes. "Repeated queries" is a hypothesis, and in my experience slow web apps more often turn out to be N+1 query patterns, a missing index, or connection-pool contention. Those have fixes that are both cheaper and safer than caching. If you can turn on slow query logging or add request-level timing for a day, we'll know rather than guess.

If caching genuinely is the answer, the shape that works with your constraints:

- **Shared cache** (Redis or memcached) rather than per-process dicts, so all eight workers see the same state
- **Explicit keys** you construct — `docs:v1:user:{id}:archived:false` — never the raw SQL, so the auth scope is visibly part of the key
- **TTL on everything** as a backstop, plus explicit invalidation on write
- **Applied selectively** to queries you've measured as hot and that tolerate brief staleness — reference data, config, expensive aggregates. Not to user-scoped reads on the write path

That's more work than a global dict, which is the honest tradeoff: correct caching in a multi-process, multi-tenant, write-heavy app is a real project rather than a one-afternoon change.

Want me to start with the measurement side — instrument the request path and pull out the actual slow queries? That'll tell us whether any of this caching work is needed at all.