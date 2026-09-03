I can build a caching layer, but not that one — keyed by SQL string in a per-process global, it would serve one user's rows to another. Here's the reasoning, then what I'd build instead.

## Three problems with the plan as stated

**1. The cache key is a cross-user data leak.** Your authorization lives in the `WHERE` clause. If those queries use bound parameters — the normal case — every user hits the *same* SQL string:

```sql
SELECT * FROM documents WHERE owner_id = ? AND deleted_at IS NULL
```

User A populates the cache; user B's request finds a key hit and gets A's documents. This isn't a rare race — it's the steady state for any hot query. It fails exactly where you'd least want it to: your authorization boundary.

If instead you interpolate values into the SQL text, the keys are distinct and safe, but now every user has a private copy of every query and the hit rate collapses toward zero — you've paid for a cache that mostly misses.

**2. Eight workers means eight caches.** A process-global dict isn't shared. You get one-eighth the hit rate you're imagining, eight copies of the memory, and — worse — eight different answers to the same question. A user whose write lands on worker 3 sees their change; refresh hits worker 6 and it's gone. Load balancers make that look intermittent and nearly impossible to reproduce.

**3. 400 writes/min with no invalidation.** That's ~7 writes/sec continuously mutating data that the cache never hears about. Reads go stale within seconds of the first write touching that table, and stay stale forever, since a plain dict has no TTL and no eviction. It's also an unbounded memory leak: every distinct query string is retained for the life of the process until the worker OOMs or gets recycled.

## What I'd build instead

**Per-request memoization — do this first.** A dict scoped to a single request, discarded when the request ends. Same user, same transaction, same instant in time, so all three problems above vanish. It kills N+1 duplicate queries, which in my experience is where "repeated queries" usually come from:

```python
def cached_query(sql, params):
    key = (sql, params)                    # params included, not just SQL
    cache = request_context.query_cache    # per-request, not global
    if key not in cache:
        cache[key] = tuple(db.execute(sql, params).fetchall())
    return cache[key]
```

Returning a tuple, not the live cursor rows, so a caller mutating the result can't corrupt what the next caller sees.

**Cross-request caching only for data that isn't user-scoped.** Lookup tables, config, feature flags, plan tiers — no `WHERE user_id`, so SQL-plus-params keying is genuinely safe and hit rates are high. Put it in Redis or memcached so all eight workers share it, with a bounded size and a TTL you can live with.

**For user-scoped data, if you still want it cached:** shared store, key includes the full parameter tuple *and* the authenticated user/tenant ID as an explicit component (not just implicitly via params), short TTL as a backstop, and explicit invalidation on write — tag cached entries by table and drop the tag's entries when that table is written. At 7 writes/sec you'll be invalidating constantly, which is the honest signal that this data may not be worth caching.

**Before any of it, measure.** Turn on slow-query logging or APM for a day and find which queries actually dominate your p95. The usual answer is one missing index or one N+1 loop, and fixing it beats any cache — no staleness, no invalidation logic, no new failure mode. Caching is what you reach for after the query itself is as fast as it's going to get.

## Where I'd start

Point me at the repo and I'll do the measurement pass first, then implement per-request memoization — that's the piece that delivers most of "repeated queries are instant" with none of the cross-user exposure. If the numbers say you need cross-request caching after that, I'll build it on Redis with the key structure and invalidation above.

One caveat: I'm working from your description, not the code. If your authorization is enforced somewhere other than the `WHERE` clause — a per-user connection, RLS in Postgres, a separate schema per tenant — the leak analysis changes and I'd want to re-check it against what's actually there.