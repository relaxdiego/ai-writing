## Short version

The idea is sound in outline — but this specific implementation would, with high probability, serve one user's rows to another user. That's the part I'd want to fix before anything else. The rest of the concerns are ordinary cache problems, but that one is a security incident.

## The dangerous part: keying by the SQL string

Your authorization lives in the WHERE clause. If you use parameterized queries (and I hope you do), the SQL string sent to the driver is identical for every user:

```sql
SELECT * FROM invoices WHERE org_id = ? AND user_id = ?
```

Alice and Bob produce the *same cache key* and different result sets. First request populates, second gets someone else's data. It's not an edge case — it's the common path, and it hits hardest on your most-repeated queries, which are exactly the ones you're caching.

If instead you interpolate values into the SQL text, the key is unique per user, and you get correctness at the cost of a hit rate near zero (plus you have a SQL injection surface). Either way the premise doesn't hold.

**Rule to carry forward:** a cache key must include everything the result depends on — and the authorization scope is part of the result, not part of the request plumbing.

## Three more that will bite

**Eight processes, eight dictionaries.** A per-process dict isn't a cache for your app, it's eight caches with ~1/8 the hit rate each and 8× the memory. Worse, it's *incoherent*: the same user refreshing twice hits different workers and sees different data, so bugs show up as "sometimes it's stale" — the hardest kind to reproduce.

**400 writes/min against no invalidation.** That's a write every 150ms. Without invalidation, cached reads go stale within seconds of being written, and users will see their own writes fail to appear — the single most-reported and least-tolerated staleness bug. Read-your-own-writes is the baseline expectation.

**Unbounded dict.** No eviction, no TTL, no size cap. Distinct query strings accumulate for the process lifetime; workers grow until the OOM killer takes them. Slow, and it looks like a memory leak rather than a cache problem.

## What I'd suggest instead

**First, measure.** "Repeated queries are slow" is a hypothesis. Turn on the slow query log and get p95 latency broken down by endpoint. In my experience the actual culprit is usually N+1 queries in a loop, a missing index, or connection-pool exhaustion — all of which caching *hides* rather than fixes, and all of which are cheaper to fix properly. If one endpoint is 80% of your database time, you may not need a cache at all.

**If caching is genuinely the answer**, the shape I'd reach for:

- **Shared store** (Redis/memcached), not per-process dicts — one coherent cache across all eight workers.
- **Explicit keys at the call site**, not derived from SQL text: `invoices:v1:org:{org_id}:user:{user_id}:page:{n}`. Explicit keys make the auth scope visible and reviewable.
- **Short TTLs** (30–60s) as a safety net, plus **explicit invalidation on write** — delete or bump the relevant keys in the same code path that does the UPDATE.
- **Bypass the cache for read-after-write**: after a user writes, read them through to the database for a few seconds so they always see their own changes.
- **Cache a few specific hot queries**, not everything. Caching is a correctness liability on every query it touches; you want that liability on the ten queries that pay for it, not all of them.

Also worth checking before you build any of this: connection pool sizing, and whether read-heavy endpoints can go to a read replica or be cached at the HTTP layer for anonymous traffic. Those are often larger wins with far less risk.

## If you want to move fast anyway

The minimum viable safe version: shared Redis, keys that include the user/org scope, 60s TTL, applied to your top three slowest read endpoints only. That gets you most of the benefit in an afternoon without the cross-user leak.

Happy to start on either path — want me to profile the slow queries first, or go straight to wiring up the scoped cache?