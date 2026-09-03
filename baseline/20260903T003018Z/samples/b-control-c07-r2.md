I'd push back on this one — not because caching is wrong, but because keying by SQL string specifically collides badly with the three facts you mentioned.

## The blocking problem: authorization

If you use parameterized queries (and you should be), the SQL string is *identical* across users — only the bound parameters differ:

```sql
SELECT * FROM invoices WHERE org_id = $1 AND user_id = $2
```

Cache that by SQL text and user B gets user A's rows on a hit. That's a cross-tenant data leak, and it's the kind that shows up in an audit rather than in your error logs, because nothing crashes — the wrong data just renders successfully.

The "fix" of interpolating values into the cache key gets you back to correct-but-useless: the key now varies per user, so your hit rate collapses to roughly "how often does one user repeat their own query," which is a much smaller number than you're imagining.

## Two more that bite regardless

**Eight processes, eight caches.** A per-process global dict means 8 independent copies. You pay 8× the memory, get roughly 1/8 the hit rate you're modeling, and each worker goes stale on its own schedule — so the same user hitting refresh gets different answers depending on which worker the LB picks. That's a very unpleasant class of bug report.

**400 writes/min with no invalidation story.** That's ~7 writes/sec, each potentially invalidating an unknown set of cached reads. Keyed by SQL string, you have no way to compute which entries a given `UPDATE` invalidates — there's no mapping from "row 4821 changed" back to "these 340 query strings touched it." The usual fallback is a TTL, which just converts a correctness bug into a time-boxed correctness bug. Also worth noting: a plain dict with no eviction is an unbounded memory leak with extra steps.

## What I'd actually do

**Measure first.** Turn on `pg_stat_statements` (or the MySQL slow query log) and find the actual top-10 queries by total time. In my experience this is usually not "the same query repeated" — it's an N+1 loop or a missing index, and caching would paper over it at considerable cost.

**Then, in rough order of value per unit of risk:**

1. **Fix indexes and N+1s.** Boring, but it's typically a 10–100× win on the specific queries that hurt, with zero staleness risk.
2. **Request-scoped memoization.** This is the safe subset of your idea, and I'd genuinely recommend it: a dict that lives for one request and is discarded at the end. One user, one auth context, one transaction — so no leak — and it kills the duplicate-query-within-a-request pattern that N+1s create. Cheap to add, hard to get wrong.
3. **A shared cache (Redis/Memcached) for the genuinely hot reads.** Key on *semantic identity* — `user:1234:invoice_summary:v7` — not on SQL text. All 8 workers share it, and the key includes who's asking, so authorization is structural rather than accidental. Invalidate by bumping the version segment on write.
4. **HTTP caching** for read-heavy endpoints whose data is public or per-user-cacheable. Pushes the work off your app entirely.

One thing I don't know: what's your read:write ratio? 400 writes/min is meaningful context, but whether caching is worth it at all depends heavily on whether you're serving 2,000 reads/min or 200,000. If you can pull that number plus the `pg_stat_statements` top-10, I can give you a much more specific recommendation — and if it turns out one or two queries dominate, option 3 scoped to just those is a small, contained change rather than a global architectural one.