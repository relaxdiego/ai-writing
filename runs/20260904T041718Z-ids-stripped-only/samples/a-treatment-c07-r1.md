Don't ship this version: keyed on search text alone, the cache will serve one user's private saved items to another.

The page body is a function of the query, the viewer, and what that viewer is allowed to see, but the key only captures the query. The first person to search "invoice" warms the cache with their saved items and their permission-filtered results; everyone who searches the same words for the next hour gets that page. The permission filter doesn't run at all, because the page is never rendered again. This is the kind of bug that looks fine in staging, where everyone is testing as the same account, and gets found by a customer. Adding the viewer's ID to the key closes the leak, but it also collapses the hit rate to "the same person repeated the same search," which is close to the load reduction you'd get from doing nothing.

The prices are a separate problem. An hour is a long time to show a stale number, and if those prices feed a checkout or a quote, you may end up honouring one you no longer offer. That's a business call rather than a technical one, but it should be made deliberately and not inherited from a cache TTL.

What does work here is caching the layer that's genuinely shared rather than the page. The expensive part of a search is almost always the full-text scan over public content, and that part depends only on the query text. Cache the query to an ordered list of candidate item IDs, with no permission filtering and no user data in it, and then per request:

- filter the ID list against the viewer's permissions
- hydrate the surviving IDs from the item store or a short-TTL item cache
- fetch prices live, or from a cache measured in seconds
- merge in the viewer's own saved items

Every one of those is an ID-keyed lookup, which is the cheap kind of database work. The scan you were actually trying to avoid happens once per distinct query.

Before building any of it, spend an hour with the slow query log to confirm the scan is the bottleneck. If the real cost is an N+1 in the permission check or in hydrating results, a search cache in front of it buys you very little, and the fix is a different one. Placing a cache at the wrong layer is how teams end up with a cache to maintain and a page that's still slow.

The candidate-ID cache is a small change that doesn't touch the permission path, so the week is still realistic once you know where the time is going.