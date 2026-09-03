Don't key the cache by SQL string: with parameterized queries, that key will hand one user's rows to another user.

The reason is that the authorization lives in the parameter, not in the text. If your queries look like `SELECT ... WHERE owner_id = %s AND ...`, every user in the system produces the identical SQL string, and the user id travels beside it in the parameter tuple. Whoever misses the cache first populates it, and the next seven hundred requests get that person's rows regardless of who is asking. It is a silent horizontal privilege escalation with no error and no log line, and it would be found by a customer rather than by you. The other branch is no better: if the ids are interpolated into the SQL text, then the key is distinct per user, so the bug is gone, but so is the hit rate, since almost every key is unique to one user, and you have string-built SQL in the bargain.

Three more things break even after the key is fixed. Eight worker processes means eight independent dictionaries with eight different ideas of the truth, so a user who writes and then reloads gets routed to a different worker and sees the old value. At 400 writes a minute you are invalidating something roughly every 150ms, and a process-local dict has no way to hear about a write that happened in another process. And a global dict that is never evicted grows until the worker is OOM-killed, which under a load balancer looks like intermittent 502s rather than like a cache problem.

What I would actually do:

- Profile first. Repeated-identical-query pressure usually turns out to be an N+1 loop or a missing index, and fixing that is cheaper and safer than any cache.
- If a cache is still warranted, put it in Redis or memcached so all eight workers share one view.
- Build the key from the query text plus the full parameter tuple plus the acting user or tenant id, so an authorization boundary can never be crossed by a key collision.
- Give every entry a short TTL and invalidate explicitly on write to the affected tables. The TTL is the backstop, not the mechanism.
- Bound the memory, and keep entries out of the cache entirely for tables written to on nearly every request.

Worth knowing before you choose the TTL: caching post-authorization result sets means a revoked permission stays effective until the entry expires. That is usually acceptable at 30 seconds and usually not at 30 minutes, and it is a decision about your security posture rather than about performance.