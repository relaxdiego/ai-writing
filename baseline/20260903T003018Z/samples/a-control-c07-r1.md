Short version: I'd not ship this as described — the SQL-string key combined with row-level auth in the WHERE clause is a cross-user data leak, not just a stale-data risk. But there's a version of the idea that gets you most of the speedup safely. Here's the reasoning and what I'd build instead.

## Why the global dict keyed by SQL text is unsafe here

**1. The authorization leak (the blocker).** If your queries are parameterized — `WHERE user_id = $1 AND ...` — then the SQL *string* is byte-identical for every user, and the parameters live outside the key. User A warms the cache; users B through Z get A's rows back. Your row-level authorization is enforced in a clause that the cache key throws away. That's a straightforward horizontal privilege escalation across your entire user base, and it would be nearly invisible in testing because it only shows up under concurrent multi-user traffic.

The alternative case isn't much better: if you're interpolating the user ID into the SQL text, the key is unique per user, so there's no leak — but then your hit rate collapses to per-user repeats, which is a small fraction of what you were hoping for, and string-interpolated user input is its own problem worth looking at.

Worth checking which case you're in before anything else: log a few of the actual query strings your ORM emits and see whether the user ID appears in the text or in the parameter list.

**2. Eight processes means eight caches.** A process-global dict isn't shared. You get 1/8th the warming benefit, 8× the memory, and eight independently stale views of the same data. Behind a load balancer, a user writes through worker 3 and reads through worker 5 — they don't see their own write. Read-your-own-writes violations are the bug reports that eat your week ("I saved it and it didn't save"), and they're maddening to reproduce because they depend on which worker got the request.

**3. 400 writes/min is not a read-only workload.** That's ~7 writes/sec continuously mutating the data you'd be caching, with no invalidation path in the proposal. A plain dict also has no TTL and no eviction, so it grows without bound until the worker gets OOM-killed — and with eight workers, memory pressure hits all of them at once.

## What I'd do instead

**Measure first.** Turn on `pg_stat_statements` (or your DB's equivalent) or an APM trace on a slow endpoint. In my experience, "the same query runs over and over" almost always turns out to be an N+1 loop inside a single request, or one unindexed query that dominates everything. Those have direct fixes that beat any cache — and a cache layered over an N+1 just makes the N+1 permanent.

**Then, in rough order of value-per-risk:**

- **Fix the indexes.** Least glamorous, biggest wins, zero correctness risk.
- **Request-scoped memoization.** A dict that lives for one request and dies with it, keyed by query *plus parameters*. This captures nearly all of the "identical query repeated" benefit, and it's safe by construction: one request is one user, and nothing can go stale within a few hundred milliseconds. If your ORM has an identity map or session cache, you may already have this and just need to use it correctly.
- **Cache the data that isn't user-scoped.** Reference tables, config, feature flags, category lists. No authorization dimension, changes rarely, safe to cache aggressively and share.
- **A real shared cache (Redis/memcached) for the genuinely hot user-scoped reads** — but key it on *entity identity plus the authorization scope*, e.g. `user:{id}:dashboard:v3`, never on SQL text. Set a TTL you can live with, invalidate explicitly on write, and bump the `v3` when the shape changes so deploys don't serve stale schemas. Shared across workers, so writes on worker 3 are visible from worker 5.

The rule that keeps this correct: **the cache key must contain every input the authorization decision depends on.** If the user ID determines which rows come back, the user ID belongs in the key. A SQL-string key violates this the moment your queries are parameterized, which is exactly the case you're in.

If you can point me at the codebase, I'm happy to check which query style your ORM is emitting and look for the N+1s — that would tell us pretty quickly whether you need a cache at all or just an index and a `select_related`.