Don't key the cache on the SQL string. With per-user authorization in the WHERE clause, that key will serve one user's rows to another.

The failure depends on how the user ID reaches the query, and neither case works. If it is a bound parameter, as it should be, then `SELECT ... WHERE user_id = ?` is byte-identical for every user in the system; the first request populates the entry and the next seven hundred read someone else's rows through it. If instead the ID is interpolated into the SQL text, the key is unique per user, the hit rate collapses to whatever a single user's repeated queries give you, and you have paid the memory cost for almost none of the speedup. The authorization predicate is data, not text, so the text cannot be the key.

Three other things about the shape you described, independent of that:

- Eight worker processes means eight dictionaries. Each one is cold on its own, so your hit rate is roughly an eighth of what you would estimate from request logs, and a write handled by worker 3 cannot evict anything in workers 1, 2 and 4 through 8.
- At 400 writes per minute, an unbounded cache with no invalidation serves stale reads continuously. Not occasionally under load: continuously, from the first write onward.
- A plain global dict never evicts. It grows until the worker is OOM-killed, and the restart looks like an unrelated intermittent crash.

What does work is a shared cache keyed on the authenticated principal along with the statement and its parameters, with invalidation driven by table version tags. Writes bump a counter per table; the counter values are part of every read key, so a bump orphans every cached entry that touched that table across all eight workers at once, without needing to enumerate them. At roughly seven writes a second, the bump traffic is negligible.

```python
import hashlib, json
import redis

r = redis.Redis(host="cache", decode_responses=True)
TTL = 60  # backstop; see the race note below

def _digest(principal_id, sql, params):
    payload = json.dumps([principal_id, sql, params], default=str, sort_keys=True)
    return hashlib.sha256(payload.encode()).hexdigest()

def _versions(tables):
    vals = r.mget([f"tag:{t}" for t in tables])
    return ",".join(v or "0" for v in vals)

def cached_query(principal_id, sql, params, tables, execute):
    key = f"q:{_digest(principal_id, sql, params)}:{_versions(tables)}"
    hit = r.get(key)
    if hit is not None:
        return json.loads(hit)
    rows = execute(sql, params)
    r.setex(key, TTL, json.dumps(rows, default=str))
    return rows

def invalidate(tables):
    pipe = r.pipeline()
    for t in tables:
        pipe.incr(f"tag:{t}")
    pipe.execute()
```

Four constraints on wiring it in. `principal_id` must come from the server-side session, never from a request parameter, or you have rebuilt the original bug with extra steps. `invalidate` must run after the transaction commits, not inside it, since a rollback would otherwise discard rows that the cache has already been told to forget. Reads inside a transaction that has already written should bypass `cached_query` entirely and go to the database, so a request can see its own writes. And `tables` is the set of every table the statement reads, including ones reached only through a join, because a stale join is as wrong as a stale select.

One race remains and cannot be closed by this design: a write that commits between the `mget` and the `setex` leaves a fresh-looking entry filed under the superseded version. The TTL is what bounds it, so the number you choose there is your actual staleness ceiling, not the tuning knob it looks like.

Before any of this, put timing on the query path. Caching helps when the same principal issues the same statement repeatedly within the TTL; if your slow requests are instead one expensive uncached report each, the cache adds a network hop to every query and gives back nothing, and the fix is an index.