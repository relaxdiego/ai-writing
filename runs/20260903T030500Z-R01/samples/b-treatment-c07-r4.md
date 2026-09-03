Caching is a reasonable instinct, but the specific shape you described will break correctness before it buys you speed. Three problems, roughly in order of how badly they bite.

**Keying by SQL string leaks data across users.** Your authorization lives in the WHERE clause. If you use bound parameters (`WHERE user_id = $1`), the SQL string is byte-identical for every user, so the first user to run a query populates a cache entry that every other user then reads. That's a straightforward horizontal privilege escalation. If you interpolate values into the SQL instead, the key is unique per user — but then your hit rate collapses, because almost every entry is used once. The version that's fast is the version that's unsafe. Any key you can actually trust has to include the full parameter list plus whatever connection state affects results (tenant, `search_path`, role).

**Eight processes means eight caches.** A global dict is global only within one interpreter. You get one-eighth the hit rate you're imagining, eight copies of the memory, and — worse — a user whose requests land on different workers sees results flip between fresh and stale depending on routing. That's the kind of bug that shows up as "the page sometimes shows the old value" and takes a week to track down.

**No invalidation at 400 writes/min.** That's roughly seven writes a second, each potentially invalidating an unknown set of cached reads. Without invalidation the cache is a monotonically growing pile of increasingly wrong answers, and a plain dict never evicts, so it's also an unbounded memory leak that ends in the OOM killer.

**What I'd suggest instead:**

Start by finding out where the time actually goes — enable slow query logging, or pull p95 timings per endpoint. Query caching only helps if the database is genuinely the bottleneck, and in most apps I've seen this pattern proposed for, the real cost turns out to be N+1 query patterns or a missing index. Those fixes are cheap and carry no correctness risk.

If caching is still warranted after measuring, make it explicit rather than transparent. Pick the handful of specific queries that are hot and tolerate staleness — reference tables, config, aggregate counts — and cache those by name with a hand-built key that includes the user or tenant ID. Put it in Redis or memcached so all eight workers share it, give every entry a TTL short enough that staleness is bounded even when invalidation is missed, and delete relevant keys on write.

The general principle: cache things that are expensive, stable, and *not* user-scoped. Per-user authorized rows are the worst possible candidate, because they're the case where a wrong answer is a security incident rather than a cosmetic bug.

Happy to look at your slowest queries and figure out what's actually worth caching, if you want to share the query log.