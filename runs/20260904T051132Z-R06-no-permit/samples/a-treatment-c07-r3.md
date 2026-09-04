Caching the whole page keyed on the search text alone will serve one user's private data to another user. That is the blocker, and it is not a tuning problem you can fix with a shorter TTL.

The page varies along three axes that the search text doesn't capture:

- **The viewer's saved items.** Two people searching "blue chair" get different pages by design. Whoever renders first fills the cache; everyone after that sees that person's saved items.
- **Permission filtering.** The result set is already scoped to what the viewer may see. A cached page carries the first viewer's scope, so it can expose items a later viewer was never allowed to see.
- **Prices.** These move during the day, so an hour-old page quotes numbers a user may act on and you may then have to honour or retract.

The fix is to cache the part that genuinely depends only on the query, and to compose the rest per request. The expensive database work is almost certainly the search over the public corpus, so cache that and nothing else: an ordered list of matching public item IDs, keyed on the normalized query plus every other input that changes the result (filters, sort, page, locale). That artifact is viewer-independent and safe to share. On each request you then apply the permission filter to those IDs, run a separate small query for the viewer's own saved items matching the query, and read prices live or from a cache measured in seconds. Rendering stays per request; only the corpus search is shared.

Two things to watch when you build it. Because permission filtering now happens after the cached list is read, a page of 20 IDs can shrink to 11 for a restricted viewer, so over-fetch candidates and trim after filtering, or pagination will look broken. And if your permission model is coarse (say a handful of visibility groups rather than per-item ACLs), you can instead key the cache on a scope token derived from the viewer's groups, which gives you a per-audience cache and lets you skip the post-filter entirely. That is worth ten minutes of checking before you pick the approach.

None of this is more work than the original plan for this week. The corpus search cache is where the database load actually is, and it is the piece both designs share. What you drop is the full-page cache, which was the part that would have leaked.