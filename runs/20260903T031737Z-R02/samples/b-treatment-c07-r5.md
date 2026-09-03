Caching is the right instinct, but keying on the SQL string is the one detail I'd push back on hard, because in your setup it's a data-leak vector before it's a performance question.

**The authorization problem.** If your queries are parameterized — `SELECT * FROM documents WHERE owner_id = ? AND status = ?` — then the SQL string is byte-identical for every user who runs that code path. Whoever populates the cache first wins, and every subsequent user gets that person's rows back. Row-level authorization enforced in the WHERE clause only works if the parameters travel with the query, and a SQL-keyed cache discards exactly that. The alternative failure is no better: if you're interpolating values into the string so the keys do differ per user, you have SQL injection instead of a cache bug. Any cache key has to include the bound parameters and the authenticated principal, not just the statement text.

**Eight processes, eight caches.** A global dictionary is global only inside one Python (or Node, or Ruby) process. With eight workers you get eight independent caches, each warming separately, each holding its own copy of the same rows, and none of them able to tell the others that something changed. Your load balancer will send the same user to different workers on consecutive requests, so a write that lands on worker 3 stays invisible to the seven other caches — the user updates a record, refreshes, and sees the old value roughly seven times out of eight. Memory multiplies by eight as well, and an unbounded dict has no eviction, so it grows until the worker is OOM-killed and restarts with a cold cache.

**400 writes a minute.** That's about seven per second, which means any cached read of a frequently-written table is stale almost immediately. Fixing that requires knowing which cached entries a given write invalidates, and deriving that from an opaque SQL string means parsing the SQL or maintaining table-level dependency tags by hand. Table-level invalidation on your hot tables would then clear most of the cache several times a second, so the hit rate on precisely the data you were trying to speed up collapses toward zero while you keep paying the complexity and the correctness risk.

## What I'd do instead

Start by measuring rather than guessing, because the shape of the fix depends on what's actually slow. Log per-request query counts and durations for a day and look at the top of the distribution. In my experience the culprit is usually an N+1 loop or a missing index rather than genuinely repeated identical queries, and an index costs nothing in correctness while a cache costs quite a lot.

Assuming there's still a caching story after that, I'd layer it:

- **Request-scoped memoization.** A dict created at the start of a request and discarded at the end, keyed by query plus parameters. It eliminates the duplicate-query-within-one-request problem entirely, and because a single request has exactly one authenticated principal and a millisecond-scale lifetime, both the authorization and the staleness problems disappear. This is the cheapest safe win and I'd do it first.

- **A shared cache for non-user-scoped data.** Redis or memcached, reachable by all eight workers, holding the things that are the same for everyone and change rarely: config, feature flags, reference and lookup tables, catalog data. Key these semantically (`plan_limits:v3`) rather than by SQL, give them a short TTL, and the invalidation question mostly answers itself.

- **Entity-level caching for user data, if needed.** Cache individual objects keyed by primary key with an explicit invalidation or version bump on write, and do the authorization check against the fetched object rather than relying on a WHERE clause you've cached past. Only reach for this if measurement says the per-user reads are genuinely the bottleneck.

Worth confirming too: are you running a connection pool, and are your reads able to go to a replica? Both are frequently larger wins than application-level caching and neither can serve one user another user's rows.

If you can share the slowest three or four endpoints and their query logs, I'm happy to look at which of these actually applies.