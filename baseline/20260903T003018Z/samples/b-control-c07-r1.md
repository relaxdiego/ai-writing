Caching is a reasonable instinct here, but the specific design you described will break in a way that's worse than slow: it will serve one user's rows to another user. Let me lay out why, then what I'd do instead.

## Why the global dict fails on this app

**1. Keying by SQL string leaks data across users.** Your authorization lives in the WHERE clause. If you use bound parameters — `WHERE org_id = $1 AND user_id = $2` — the SQL *string* is byte-identical for every user in the system. The first user to run it populates the cache; everyone else gets their rows. That's a critical authz bug, and it won't show up in testing because you'll usually be logged in as one user. If you instead interpolate values into the string, the key becomes unique per user, which fixes the leak but collapses the hit rate to near zero — the exact queries you most want to cache are the per-user ones that will never repeat.

**2. Eight processes means eight caches.** A global dict is per-process. You get 1/8th the hit rate you're imagining, 8× the memory, and — worse — eight different answers in flight. A user does a write handled by worker 3, refreshes, gets routed to worker 6, and sees their old data. This produces "the save didn't work" bug reports that are nearly impossible to reproduce.

**3. 400 writes/min makes invalidation the whole problem.** That's ~7 writes/sec constantly dirtying cached reads. A dict with no invalidation serves stale data within seconds. And invalidation is the hard part: when a row in `orders` changes, which cache keys does that affect? With SQL-string keys, you can't tell without parsing the SQL — you'd end up flushing everything on every write, which means the cache is empty most of the time.

**4. Unbounded growth.** No TTL and no eviction means the dict grows until the worker OOMs. With per-user keys, that happens fast.

## What I'd actually do

**First, measure — the fix probably isn't caching.** Turn on `pg_stat_statements` (or your DB's slow query log) and pull the top queries by total time, not by individual duration. In my experience the answer is usually one of: a missing index, or an N+1 loop issuing 200 small queries per request. Both are cheaper to fix than a cache layer and don't introduce correctness risk.

**Then, the safe cache that's actually free: request-scoped memoization.** A dict that lives for the duration of one HTTP request and is discarded. This kills duplicate queries within a request — which is where a lot of real waste lives — with zero staleness risk and zero cross-user risk, because the cache never outlives the authenticated context that created it. If you want a cache today, start here.

**If you still need a cross-request cache, the requirements are:**
- **Shared store** (Redis/memcached), not per-process, so all eight workers agree.
- **Key includes every bound parameter plus the authenticated principal** — user/org ID as an explicit key component, not implicitly via the SQL.
- **Explicit invalidation on write**, keyed by entity (`user:1234:orders`), plus a short TTL (30–60s) as a backstop.
- **Bounded memory** with LRU eviction.
- **Start with what isn't user-scoped**: reference tables, config, feature flags, pricing tiers. High hit rate, trivially safe, no authz surface.

**Also worth checking before you cache anything:** connection pool sizing (an undersized pool looks exactly like slow queries), and whether read-heavy endpoints can go to a read replica.

If you want, point me at the repo and I'll pull the slow query stats and check for N+1 patterns — that'll tell us whether caching is even the right lever, and if it is, which queries actually deserve it.