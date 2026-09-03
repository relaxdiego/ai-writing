Caching your reads is a reasonable instinct, but keying on the SQL string alone will serve one user's rows to another. If you use parameterized queries, the string is `SELECT ... WHERE owner_id = ?` for every user alike; the value that distinguishes them lives in the parameters, not the key. The first user to warm an entry decides what everyone else sees. (If instead you interpolate values directly into the SQL text, the key is unique per user, but then you have an injection surface and a hit rate near zero, since almost no two queries are textually identical.)

Three smaller problems come with the global dict. Eight worker processes means eight caches, so a warmed entry helps only the fraction of requests the balancer happens to route back to that worker. A write handled by worker 3 cannot invalidate anything in workers 1, 2, or 4 through 8. And at 400 writes a minute, a dictionary that is never invalidated and never expires is serving stale rows within seconds while growing without bound in all eight processes.

What actually works here is a shared cache keyed on everything that affects the result, with invalidation by table version. Sketch, adapt to your stack:

```python
import hashlib, json
from redis import Redis

redis = Redis(...)

def _key(sql, params, user_id, tables):
    versions = [ (redis.get(f"ver:{t}") or b"0").decode() for t in sorted(tables) ]
    raw = json.dumps([sql, params, user_id, versions], sort_keys=True, default=str)
    return "q:" + hashlib.sha256(raw.encode()).hexdigest()

def cached_query(conn, sql, params, *, user_id, tables, ttl=30):
    k = _key(sql, params, user_id, tables)
    hit = redis.get(k)
    if hit is not None:
        return json.loads(hit)
    rows = [dict(r) for r in conn.execute(sql, params)]
    redis.setex(k, ttl, json.dumps(rows, default=str))
    return rows

def invalidate(*tables):
    for t in tables:
        redis.incr(f"ver:{t}")
```

The user id belongs in the key even though it is already in the parameters: it is cheap insurance against a query whose authorization rides on a join or a session variable rather than an explicit bind. Writes call `invalidate` for the tables they touch, which bumps the version and makes every existing key for those tables unreachable; the orphans age out on their own TTL. The short TTL is a second line of defence for whatever you forget to invalidate.

One caution about your write rate. If those 400 writes a minute are spread across your busiest tables, version bumps will flush the cache faster than it fills, and you will have added a Redis round trip to every read for nothing. So wrap only the read paths you have measured as slow and whose tables are relatively quiet, and check your query plans first. A missing index usually beats a cache layer on both latency and the amount of correctness you have to reason about.