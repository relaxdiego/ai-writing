The plan has one flaw that matters more than the performance question, so I want to put it first. If your queries use bound parameters, which they should, then `SELECT ... WHERE user_id = ? AND ...` is byte-identical for every user who runs it. Keyed by SQL string alone, the first user to run that query populates the entry and the next seven get served their rows. That is not a slow page, it is a cross-tenant data leak with row-level authorization silently disabled. The only way the SQL string distinguishes users is if you are interpolating values into the query text, in which case the cache key works and you have a SQL injection surface instead. There is no version of "keyed by the SQL string" that is safe here.

The second problem is that a global dictionary in a Python or Node process is per process, and you have eight of them. Nothing propagates between them, so a write served by worker 3 leaves stale entries in the other seven with no mechanism that will ever clear them. At 400 writes per minute you are producing roughly seven invalidation events per second against a cache that cannot hear any of them, and users will see their own edits vanish and reappear depending on which worker the load balancer picks. A plain dict also never evicts, so each worker's resident memory climbs until the box starts swapping or the OOM killer picks a worker at random.

What I would actually build, if the profile supports caching at all, is a shared cache with a key that includes the bound parameter values and the authorization principal, a short TTL so staleness is bounded even when invalidation is missed, and a size limit. Something along these lines:

```python
key = "q:%s:%s" % (user_id, hashlib.sha256(
    json.dumps([sql, params], sort_keys=True).encode()).hexdigest())
hit = redis.get(key)
if hit is not None:
    return json.loads(hit)
rows = db.execute(sql, params).fetchall()
redis.setex(key, 30, json.dumps(rows))   # TTL bounds the damage
```

Putting the user id in the key prefix means a leak requires an actual key collision rather than merely the absence of a distinguishing field, and it lets you drop everything for one user on write by tracking their keys in a set. The TTL is doing the real work: with 400 writes a minute, whatever invalidation scheme you write will have gaps, and thirty seconds decides how long a gap can hurt.

Before any of that, though, I would want to see where the time is going, because a query cache is an expensive way to hide a missing index. Turn on slow query logging for a day, or capture per-endpoint timings, and look at whether the cost is a handful of genuinely heavy aggregate queries or a few hundred cheap ones fired in a loop. Heavy aggregates are worth caching, and they usually cache well at the result level rather than the query level, because you can invalidate them on the specific events that change them. Hundreds of cheap queries is an N+1 pattern, and caching it converts a database round trip into a Redis round trip while leaving the count unchanged, which buys you maybe a third of the latency instead of the ninety-odd percent you would get from fixing the query.

If you can share the slow query log or the endpoint timings, I can tell you which of those two shapes you have and where the cache boundary should sit.