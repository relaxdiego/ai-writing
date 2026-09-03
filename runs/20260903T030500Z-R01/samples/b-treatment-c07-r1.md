Caching is a reasonable instinct, but keying on the SQL string specifically breaks in your setup — and one of the failure modes is a data leak, not just a performance disappointment.

**The authorization problem.** If your queries are parameterized (`WHERE user_id = ?` with `[42]`), then the SQL string is identical for every user and only the parameters differ. A cache keyed on the string alone will hand user 99 the rows that were fetched for user 42. Row-level authorization enforced in the WHERE clause is exactly the case where the key must include everything the WHERE clause depends on. If you're interpolating user IDs directly into the SQL text, you dodge this — but then you have a SQL injection surface and a cache key space that grows per user anyway, so hit rates collapse.

**The eight-processes problem.** A global dictionary is global to one process. You'd get eight independent caches with eight independent views of the data, and the load balancer decides which one a request sees. A user updates a record, hits worker 3 on the next request, sees the change; refreshes, lands on worker 6, sees the old value. That's the classic "my edit didn't save… wait, now it did" bug, and it's miserable to reproduce.

**The write-rate problem.** 400 writes/minute means roughly 7 per second invalidating unknown subsets of cached reads. Without invalidation logic, a cache entry's staleness is unbounded — it's correct until someone writes, and nothing tells it that happened. Also, a plain dict never evicts, so it grows until the process is OOM-killed.

**What I'd suggest instead:**

First, measure before caching. Turn on slow query logging for a day. Very often the win is two or three missing indexes, or an N+1 loop issuing hundreds of queries per page render, and caching would just paper over it at much higher complexity.

If caching is still the answer after that, the shape that works here:

- **Shared store** (Redis/Memcached) rather than per-process dicts, so all eight workers agree.
- **Explicit cache keys** that you construct — `user:42:dashboard:v3` — never derived from SQL text. The scope is then visible in the key and impossible to accidentally share.
- **Short TTLs** as a correctness backstop, plus explicit invalidation on write for anything where staleness is user-visible.
- **Cache selectively** — the expensive, read-heavy, rarely-changing queries. Caching everything mostly caches things that were already fast.

Also worth checking before any of this: connection pooling configuration, and whether the eight workers are actually saturating the database or just waiting on it.

Happy to start with the slow query log if you can get me a day's worth — that'll tell us whether this is a caching problem at all.