Caching is the right instinct, but keying on the SQL string alone will break in three specific ways given your setup:

**Authorization bypass.** If your queries are parameterized (`WHERE user_id = ?`), the SQL string is byte-identical for every user. User A's rows get cached, and User B's request hits that key and gets them back. This is a data leak, not a performance bug, and it will not show up in testing where you're logged in as one user.

**Eight caches, zero invalidation.** Each worker gets its own dictionary. At 400 writes/min, a write served by worker 3 leaves workers 1, 2, 4–8 serving stale rows with no idea anything changed. Users will see writes vanish and reappear depending on which worker the load balancer picks.

**Unbounded growth.** A dict keyed by SQL text with no eviction is a memory leak. Any query with interpolated values (dates, IDs, search terms) generates unique keys forever until the worker OOMs.

The version that works:

1. **Key on SQL + bound parameters + the authenticated principal.** The user identity goes in the key, not just the WHERE clause. Better still, cache above the query layer — cache the authorized result for a user — so authorization is evaluated before the cache, never after.
2. **Use a shared store** (Redis or memcached) instead of per-process dicts, so all eight workers see one cache and one invalidation.
3. **Invalidate on write.** Tag cached entries by the tables or entities they touch, and drop those tags when a write commits. If that's too much surgery for now, short TTLs (30–60s) plus explicit invalidation on the few highest-traffic entities gets most of the benefit.
4. **Set a memory bound and eviction policy** from day one.

Before any of that, though: do you know which queries are actually slow? A caching layer is a lot of machinery, and at 400 writes/min the invalidation traffic is real. If the hot path is two or three unindexed queries, an index or a fixed N+1 loop is a smaller change with a bigger win. If you can share slow-query logs or an APM trace, I can tell you which of these you actually need — and I'm happy to implement whichever direction you pick.