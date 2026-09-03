Don't ship this one. Keyed by the SQL string, a shared cache will serve one user's rows to another.

The mechanism is your authorization design meeting your cache key. If you use bound parameters, `SELECT * FROM invoices WHERE org_id = ? AND user_id = ?` is byte-identical for every user in the system; only the parameters differ, and they aren't in the key. The first request to run that query fills the entry, and every subsequent user gets that result back. The row-level checks in the WHERE clause still execute, but nobody reaches the database to run them. If instead you interpolate values into the SQL text, the key does vary per user, and you get the opposite failure: near-zero hit rate on exactly the per-user queries you were trying to speed up, plus a dictionary that grows one entry per distinct value you ever substitute.

Two more things break at your scale. Eight worker processes means eight independent dictionaries, so a write handled by worker 3 leaves the other seven serving the old value until something evicts it, and with a plain global dict nothing does. At roughly 400 writes a minute you are producing stale entries continuously, not occasionally. And an unbounded dict with no TTL and no eviction is a memory leak with a slow fuse; it will look fine in staging and page you in production.

What I'd do instead, roughly in order of payoff:

1. Find out what is actually slow. Turn on slow query logging and look at the top ten by total time, not by single-execution time. Repeated-query pain is usually N+1 access patterns or a missing index, and caching the result papers over a fix that costs you one migration.
2. Cache at specific call sites rather than under the driver. You then know what the data is and how stale it may safely be.
3. Build keys from the query plus the full parameter tuple plus the authenticated principal, so an entry can never cross a tenant or user boundary.
4. Put entries in Redis or memcached rather than process memory, so all eight workers share one view and one invalidation, with a short TTL as a backstop.

There is one place your original instinct works nearly as stated: queries with no per-user predicate at all, such as reference tables, feature flags, and config rows. Those are safe to hold in process memory keyed by SQL text, because there is no principal to leak across. That set is usually small, and it is worth carving out explicitly rather than reaching for it as a general layer.