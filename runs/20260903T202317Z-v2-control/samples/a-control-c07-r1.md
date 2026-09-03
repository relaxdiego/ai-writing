Caching is the right instinct, but the key is wrong in a way that would leak data. Keying on search text alone means the first person to search "invoice" fills the cache with *their* saved items and *their* permission-filtered results, and everyone who searches "invoice" for the next hour gets that page. That's a cross-account data exposure, not a performance bug — and it's the kind that shows up in an incident report rather than a latency graph.

The prices are a second problem: an hour-long TTL on a rendered page means users see prices that are up to an hour stale, and they'll see them on the page where they decide to buy.

What I'd do instead — same week, similar win:

**Cache the expensive part, not the page.** The costly step is almost certainly the search index/DB query over public items. Cache *that* result set, keyed on `(normalized query, filters, sort, page)` — no user identity in it, because no user-specific data is in it. Then per request, on top of the cached IDs:

- fetch the viewer's saved items (small, indexed, per-user cacheable separately)
- apply permission filtering
- fetch current prices (short TTL, seconds to a couple of minutes, keyed by item ID so a price change invalidates one entry instead of every page)

**Watch out for pagination.** If you cache 20 candidate IDs and permission filtering drops 9, the viewer sees a short page. Over-fetch (cache 3–5× the page size) or cache per permission cohort if your model has a small number of distinct visibility groups.

**Measure before you build.** One day of timing on the search endpoint — query time vs. rendering vs. the per-user joins — tells you whether the shared query is actually the hot spot. If it turns out the saved-items join is what's slow, the cache above buys you nothing and an index buys you everything.

Two things worth deciding now, since they change the design: does an item's visibility depend on per-user rules (sharing, ACLs) or on a small set of groups? And how stale can a price be before it's a problem — seconds, or a few minutes? The first determines whether cohort caching is viable, the second sets the price TTL.

If you want, I can look at the current search query path and come back with where the time actually goes.