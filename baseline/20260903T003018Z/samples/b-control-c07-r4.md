Short version: the caching layer is doable, but the design as described has one bug that leaks data across users and several that make it not actually fast. Let me lay out what breaks, then what I'd build instead.

## The blocking problem: SQL string is the wrong cache key

If you use parameterized queries — and I'd assume you do — then two different users hitting the same endpoint produce the *identical* SQL string:

```sql
SELECT * FROM invoices WHERE org_id = ? AND user_id = ?
```

The parameters differ; the key doesn't. User A's rows get served to User B. Since your authorization is enforced in the WHERE clause rather than in a separate check after the fetch, the cache read bypasses your entire authz model — there's no second gate to catch it.

This isn't a rare race. It's the steady state on every shared endpoint, and it would probably read as normal traffic in your logs until someone notices they're looking at another account's data.

(If you're doing string interpolation instead of parameters, the key is unique per user — but then you have a SQL injection surface and a cache that never gets a hit twice, which is its own answer.)

## Three more that matter

**Eight processes, eight caches.** A global dict is per-process. Your load balancer scatters requests, so each worker builds its own copy: 1/8th the hit rate you're imagining, 8× the memory, and eight independently-stale views of the same rows. Nothing invalidates across the group — worker 3 has no idea worker 6 just wrote.

**400 writes/min makes invalidation the entire problem.** That's ~7 writes/sec continuously mutating the set you're caching. A SQL-string key gives you no way to answer "which cache entries did this UPDATE invalidate?" — you'd have to parse the statement, resolve table and row, and map back to every cached query that touched them. The usual fallback is flush-the-table-on-any-write, which at 7 writes/sec means the cache is empty most of the time and you've added latency for nothing.

**Unbounded growth.** No eviction, no TTL, no size cap. It's a memory leak with a slow fuse; the process gets OOM-killed sometime after deploy, usually under peak traffic.

## What I'd do instead

**First, measure — this may not be the bottleneck.** For most apps at this write rate, the wins are N+1 query patterns, a missing index, or connection pool exhaustion, and they're bigger than caching would be. An hour with query logs sorted by total time tells you whether repeated identical queries are even a real share of your load. Worth doing before building anything.

If caching is genuinely the answer, in escalating order:

**1. Request-scoped memoization.** A dict that lives for one request and is discarded. Kills the "same lookup 40 times while rendering a page" pattern, cannot go stale (nothing can change mid-request), no cross-user exposure. Cheap, safe, often the bulk of the benefit.

**2. Shared cache for slow-changing reference data.** Redis or memcached, for the stuff that isn't user-scoped: feature flags, plan tiers, category lists, config. Shared across all eight workers, TTL in minutes, and staleness is harmless because nobody notices a category list being 60 seconds old.

**3. Explicit per-query caching where it pays.** Not automatic on every query — chosen deliberately, with keys you construct yourself:

```
invoices:v2:org=<org_id>:user=<user_id>:page=<n>
```

Tenant and user identity are *in the key*, so isolation holds structurally. The `v2` lets you invalidate a whole class by bumping it. Each cached query gets an explicit invalidation rule written alongside the write path that touches it, plus a short TTL as a backstop for the rules you'll inevitably miss.

One caution for step 3: cached reads inside a transaction can show a user data that contradicts a write they just made. Simplest rule is to bypass the cache entirely for reads within a write transaction.

## The tradeoff

The automatic version is appealing because it's ~20 lines and touches nothing else. The version I'm describing is more work and needs a Redis dependency you may not have. That's a real cost and I don't want to hand-wave it.

But the automatic version's simplicity comes from *not knowing what it's caching* — and that's exactly why it can't tell users apart or figure out what a write invalidates. There isn't a variant that keeps the simplicity and fixes the isolation; the knowledge you'd need to add is the work.

Want me to start with the query-log analysis, or go straight to adding request-scoped memoization since that one's safe regardless of what the profiling says?