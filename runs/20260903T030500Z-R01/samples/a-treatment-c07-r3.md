I'd push back on this specific design before building it — the row-level auth is what makes it unsafe rather than just imprecise.

**The keying problem.** If you key on the parameterized statement (`... WHERE owner_id = ?`), every user's version of that query collapses to one key, and whichever request misses first populates the entry that everyone else then reads. That's a cross-account data leak, not a performance bug. If you key on the fully-interpolated SQL with the user id baked in, the leak goes away — but so does most of the benefit, since the cache is now partitioned per user and the hit rate on user-scoped queries is a fraction of what a global dict implies.

**Two more things that don't survive your deployment shape:**

- Eight worker processes means eight independent dictionaries. A write served by worker 3 can't evict worker 6's copy, so you get eight divergent views of the same row and no way to reconcile them.
- At 400 writes/min something is invalidated roughly every second and a half. A plain dict has no eviction either, so it grows for the life of the process — an unbounded memory leak on top of the staleness.

**What I'd build instead, roughly in order of payoff:**

1. **Find out what's actually slow first.** Indiscriminate query caching is usually the wrong lever; the wins are typically a handful of N+1 access patterns and two or three missing indexes. That's worth an hour before we cache anything.
2. **Shared cache, not per-process** — Redis or memcached, so all eight workers see one copy and invalidation works.
3. **Key on statement + every bound parameter + the authorizing user/tenant id**, so a cache entry can never be served across an authorization boundary even if a WHERE clause changes later.
4. **Invalidate by entity, not by SQL string.** Writes tag the affected table/row ids and drop the dependent keys; TTLs are the backstop, not the mechanism.
5. **A per-process dict is fine for one thing:** non-user-scoped reference data (config, lookup tables, feature flags) behind a bounded LRU with a short TTL. That part of your idea works as-is.

If you point me at your slowest endpoints — or turn on slow-query logging for an hour — I can find where the time is actually going and scope this against real numbers.