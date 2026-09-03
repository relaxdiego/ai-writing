Caching is the right instinct, but keying by the SQL string in a per-process dict has a data-leak bug in it, not just a performance limitation. Here's the problem and what I'd build instead.

## The blocking issue: the key is wrong

Your row-level authorization lives in the `WHERE` clause. If you use parameterized queries — and you should be — the SQL string is byte-identical for every user:

```sql
SELECT * FROM documents WHERE owner_id = ? AND status = ?
```

User A runs it, the result set lands in the dict under that string, and user B's request gets a cache hit and reads user A's rows. That's a cross-tenant authorization bypass served at cache speed, and it won't show up in testing unless you specifically test concurrent users with overlapping queries.

The only way the string-as-key scheme is *not* a leak is if you're interpolating user IDs directly into SQL text, which trades the leak for an injection surface and a near-zero hit rate (every user gets their own cache entry, so nothing is shared and you're paying memory for nothing).

**The cache key must include the parameter tuple and the authorization principal.** Not the SQL alone.

## Three more problems worth knowing about

**Eight workers, eight caches.** A global dict is per-process. A write served by worker 3 leaves workers 1, 2, 4–8 holding stale data with no way to hear about it. At 400 writes/min you're producing roughly 7 invalidation events per second that 7 out of 8 workers will miss.

**Unbounded growth.** A dict with no eviction and no TTL grows until the worker is OOM-killed. Multiply by 8 processes on the same box.

**Blanket caching hides the real cost.** Caching every query means caching the cheap ones too, and paying serialization plus memory for queries that were already 0.3ms.

## What I'd do instead

**1. Move the cache out of process.** Redis or Memcached, shared by all eight workers. One cache, one invalidation, no divergence. This is the change that makes the rest of it correct.

**2. Cache objects by ID, not authorization-filtered result sets.** Instead of caching "the documents user A can see," cache `document:{id}` and keep the authorization check in the request path. The cached data is then user-independent, entries are shared across users (so your hit rate actually goes up), and an authorization change takes effect immediately rather than at TTL expiry. This inverts the leak risk — the cache no longer holds anything that depends on who asked.

Where you do need to cache a filtered set, key it explicitly:

```python
key = f"q:{query_id}:{user_id}:{hash(params)}"
```

`query_id` being a stable name you assign, not the raw SQL — that keeps the key short and survives whitespace changes in the query.

**3. Invalidate on write, with a TTL as backstop.** Tag entries by table and drop the tag's entries when that table is written. TTLs of 30–60 seconds catch whatever the explicit invalidation misses. At 400 writes/min the invalidation traffic is trivial; what matters is the fan-out — a write to a hot table that dumps a large tag will hand you a thundering herd on the next request wave. Add single-flight (one request recomputes, the rest wait) if you see that.

**4. Start with the ten slowest queries, not all of them.** Turn on slow-query logging first. In most apps this shape, the actual win is a missing index or an N+1 in a loop, and caching just puts a faster surface over a query that shouldn't be running that often. Caching a 4-second query is a workaround; caching a 4-second query you could have made 40ms with an index is a workaround you'll maintain forever.

## What this costs you

A shared cache is a new piece of infrastructure — a Redis instance, a connection pool per worker, and a decision about what happens when it's down (fail open to the database, don't fail the request). That's genuinely more work than a dict. But the dict version can't be made correct across eight processes no matter how much you tune it, and the key-collision bug is a security incident rather than a stale-data annoyance.

If you want, point me at the codebase and I'll find the slow queries and sketch the cache layer against your actual query patterns.