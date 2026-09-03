The plan will leak data between users, and I'd rather flag that before you ship it than after. The speedup you're after is real and reachable, so here's the problem and then a version I'd actually run.

## The SQL string can't be the key when auth lives in the WHERE clause

There are two cases and both go wrong. If your queries are parameterized — the normal, correct case — then `SELECT * FROM orders WHERE user_id = ?` is byte-identical for every user on the system, and only the bound parameter differs. A dictionary keyed on that string caches whatever rows the first caller was entitled to, and hands them to the next caller regardless of who they are. Row-level authorization enforced in the WHERE clause is exactly the pattern this breaks: the check still runs, it just runs on a request that never reaches the database. The other case is that you interpolate user IDs into the SQL text, which makes keys unique per user and therefore safe, but collapses your hit rate to near zero on precisely the queries you were trying to speed up, while the key space grows with your user count.

## Eight processes means eight caches and no invalidation

A module-level dict lives inside one Python process. With eight workers behind the load balancer you get eight independent copies, and nothing propagates between them — a write handled by worker 3 leaves the other seven serving the pre-write value. At roughly 400 writes per minute you're mutating state about seven times a second, so the window where some worker is confidently wrong is not an edge case, it's steady state. Even within a single worker, a plain dict has no eviction and no expiry, so entries accumulate result sets until the process is restarted or the box runs out of memory, and the only invalidation strategy available is a deploy.

## What I'd build instead

Move the cache out of process into Redis or memcached so all eight workers share one view, and make three changes to the key. Include the authenticated principal explicitly rather than trusting it to be implied by the query text, include the full bound parameter tuple, and include a generation counter per table the query touches. The generation counter is what makes invalidation tractable at your write volume: instead of enumerating and deleting keys on every write, you bump an integer, and every key derived from the old generation becomes unreachable and ages out on its own.

```python
def cache_key(sql, params, principal_id, tables):
    gens = redis.mget([f"gen:{t}" for t in tables])   # one round trip
    raw = json.dumps([sql, params, principal_id, gens], sort_keys=True, default=str)
    return "q:" + hashlib.sha256(raw.encode()).hexdigest()

def cached_query(sql, params, principal_id, tables, ttl=300):
    key = cache_key(sql, params, principal_id, tables)
    hit = redis.get(key)
    if hit is not None:
        return json.loads(hit)
    rows = db.execute(sql, params).fetchall()
    redis.setex(key, ttl, json.dumps(rows, default=str))
    return rows

def after_write(tables):                              # call inside the write txn's commit hook
    for t in tables:
        redis.incr(f"gen:{t}")
```

The TTL is a backstop, not the invalidation mechanism — it bounds how long a bug in your table-tagging can serve stale rows. Note the cost this adds: two network round trips to Redis on the read path, which is only a win if the query you're replacing is meaningfully more expensive than that. For a query the database answers from an index in under a millisecond, this design is slower than no cache at all.

## Where the actual wins are

Because the principal is in the key, per-user query results only benefit from a single user repeating themselves within the TTL, which is usually a modest hit rate. The large wins come from data that has no per-user component — reference tables, config, catalog and pricing data, feature flags — and those can be cached without the principal in the key and shared across every request on every worker. I'd carve those out as an explicit allowlist of cacheable queries rather than caching everything and trying to reason about which entries are safe.

Before wiring any of it up, get `pg_stat_statements` (or the equivalent for your engine) to tell you which queries actually dominate total time. Repeated-identical-query load is one cause of slowness, but N+1 access patterns and missing indexes are the more common ones, and a cache in front of either hides the problem while adding a correctness surface you now have to maintain. If you can tell me what the top few queries look like and roughly how your reads split between per-user and shared data, I can size the TTLs and tell you whether the Redis hop pays for itself.