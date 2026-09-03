Caching your read path is worth doing, but keying on the SQL string alone is the one variant that can't be made safe here. With parameterized queries, a row-level-authorized `SELECT ... WHERE owner_id = ?` has byte-identical text for every user; only the bound parameter differs. Keyed by text, the first caller's rows get served to every subsequent caller of that query, which is an authorization bypass rather than a staleness tradeoff. Even keyed correctly, a plain global dictionary lives inside one process, so you'd have eight independent caches with no way for a write in worker 3 to invalidate the copies held by the other seven; at 400 writes/min you'd be serving stale reads continuously, not occasionally. And an unbounded dict never evicts, so each worker's resident memory grows for as long as it stays up.

What you want instead is the same idea with three fixes: a shared store so all eight workers agree, a key that includes everything the result depends on, and invalidation driven by writes. Redis is the usual choice.

```python
def cached_query(sql, params, principal, tables, ttl=60):
    vers = redis.mget([f"v:{t}" for t in tables])   # per-table version counters
    key = "q:" + sha256(dumps([sql, params, principal, vers])).hexdigest()
    hit = redis.get(key)
    if hit is not None:
        return loads(hit)
    rows = db.execute(sql, params)
    redis.setex(key, ttl, dumps(rows))
    return rows

def after_write(tables):
    for t in tables:
        redis.incr(f"v:{t}")    # every key built on the old version is now unreachable
```

The principal goes into the key even though it's already in `params`, so that a query someone later forgets to parameterize can't silently collapse two users' entries into one. The table version counters turn invalidation into a single `INCR` per written table: stale entries become unreachable immediately and age out under the TTL and `maxmemory-policy allkeys-lru`, which also bounds memory. Serialize on the way in and out rather than storing live objects, so a caller mutating its result doesn't corrupt what the next caller sees.

Two behaviours to decide deliberately. Read-your-own-writes breaks unless you bypass the cache for the remainder of any request that performed a write, and inside any open transaction; the version bump is visible to other requests immediately but your own uncommitted rows are not. And with 400 writes/min spread across your tables, a hot table's counter may advance often enough that its cached entries rarely survive to be reused, which is the correct outcome but means the cache buys you nothing there.

That last point is the reason to instrument before you build the layer. Log query fingerprints with their counts and total time for a day, and you'll find whether the win is real repetition of a handful of reads, in which case caching those five explicitly is simpler and safer than a blanket interception layer, or whether it's an ORM issuing N+1 queries per request, which a join or an eager load fixes outright and a cache only papers over. The instrumentation also tells you which tables to tag, since a query joining three tables must be invalidated by writes to any of them.