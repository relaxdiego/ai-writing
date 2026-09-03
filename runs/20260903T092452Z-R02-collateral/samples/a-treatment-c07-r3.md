Don't key the cache on the SQL string alone: with parameterized queries, that is a cross-user data leak.

Your authorization lives in the WHERE clause, and under any parameterized driver the SQL text is byte-identical for every user who runs that query. Only the bound parameters differ. So `SELECT * FROM documents WHERE owner_id = $1` run for user 7 populates the entry that user 9 reads a moment later, and user 9 receives rows they have no permission to see. Nothing raises an error, nothing appears in the logs, and the leak is worst exactly under load, because that is when the hit rate is highest. The alternative case is no better for you: if your queries inline the user id as a literal instead of binding it, the key is safe but each user gets a private keyspace, and the hit rate collapses to whatever a single user repeats within their own session.

The eight workers create a second problem independent of the first. A global dictionary lives inside one process, so you have eight caches, not one. Each entry is computed up to eight times, which blunts the win you are after, and a write served by worker 3 has no way to reach the copies held by the other seven. At 400 writes per minute that is roughly seven stale reads waiting to happen for every write, with the staleness window bounded only by process lifetime, since a plain dict has no TTL. It also has no eviction, so the dictionary grows until the worker is killed.

A version of this that works:

- Build the key from the query text, the full tuple of bound parameters, and the authenticated principal id. Include the principal even when the parameters already contain it, so that a future authorization bug cannot become a cross-user leak.
- Move the cache into a store the workers share, such as Redis, so one invalidation reaches all eight.
- Give every entry a TTL, short enough that a missed invalidation self-heals, and a max size with LRU eviction.
- Invalidate on write by tagging each entry with the tables it read, then dropping the tags a write touches. This is coarse and will throw away more than strictly necessary, which is the right trade at your write volume.
- Cache read-mostly data only. Anything read inside a transaction that then writes should go straight to the database.

Before building any of it, get the slow query log or a profiler onto the read path. Four hundred writes per minute is a light write load, so if the application feels slow the cause is more likely a missing index or an N+1 loop issuing hundreds of small queries per request. A cache in front of either of those converts a query-plan problem into a correctness surface you have to maintain forever, and the profile usually names one or two queries where an index removes the need for the cache entirely.