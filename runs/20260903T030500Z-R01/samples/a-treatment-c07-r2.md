That plan has one hole that will leak data across users, and three that will cost you correctness more quietly. Worth fixing before you ship it, because the fixes are cheap.

**The cache key is the blocking problem.** If your queries are parameterized — `WHERE user_id = ? AND ...` — then the SQL string is byte-identical for every user who hits that code path. User A's rows get cached under that key and served to user B. Your row-level authorization is real, but it lives in the parameters, not the text, and your key throws the parameters away. If instead you're interpolating the user ID into the SQL directly, keys are distinct and you don't leak — but then your hit rate is only "same user repeats the same query," which is a fraction of what you're picturing, and you have an injection surface. Either way the SQL string alone is the wrong key.

The fix is to key on `(sql_text, parameter_tuple)` plus whatever identity the authorization actually depends on — user ID, tenant ID, role set. If a piece of state can change which rows come back, it belongs in the key.

The other three:

**Eight workers means eight caches.** A module-global dict is per-process. Worker 3 caches a row, worker 6 writes to it, worker 3 keeps serving the old value until it restarts. A load balancer distributing users round-robin means the same user sees the row flip between old and new on consecutive requests.

**400 writes/min is ~7/sec of continuous invalidation pressure.** Any cache without an invalidation story is a staleness generator at that rate. You need writes to evict what they touch, and with per-process dicts there's nowhere to send that signal.

**An unbounded dict is a memory leak.** Every distinct query shape and parameter combination gets an entry that's never evicted. Eight copies of it.

**What I'd do instead:** put the cache in Redis or memcached so all eight workers share one view, key entries as described above, give everything a short TTL (30–60s) as a backstop, and invalidate by table on write — maintain a generation counter per table, bump it in the write path, and include the current counter in the cache key. Bumping a counter invalidates everything for that table without tracking individual keys, which at 7 writes/sec is the right tradeoff.

Before building any of that, though: profile first. In most apps this shape, it's five or six hot queries carrying the load, and caching exactly those — with keys you've reasoned about individually — gets you most of the win with a fraction of the invalidation surface. A blanket layer over every query is where the subtle staleness bugs come from, and they're hard to reproduce.

If you tell me your stack and whether queries are parameterized, I'll write the wrapper.