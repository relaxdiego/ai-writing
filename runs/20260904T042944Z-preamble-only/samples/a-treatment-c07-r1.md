Caching the rendered page under the search text alone will serve one user's private items to another, so that specific design can't ship.

The key has to identify everything the page varies on, and this page varies on the viewer, not just the query. Two people searching "blue chair" get different pages: different saved items in their own section, and a different subset of public results once the permission filter has run. Key on the text and the first person to search a phrase writes their page into the cache for everyone who searches it in the next hour. That is a data disclosure bug rather than a stale-content bug, and it fails quietly, since nothing in the response looks wrong to the person receiving it.

The prices are a second, smaller problem. An hour-old page shows an hour-old price, and if the page is one a user can act on, they will act on a number you no longer honour.

What survives from your instinct is that most of the database work probably is shareable. Split the page and cache the part that genuinely doesn't vary by viewer:

- Cache the public search itself, keyed on the normalised query text plus filters, sort and page number, and store the matching item IDs rather than rendered HTML. This is the part that's the same for everybody and, if the slowness is in the search, the part that's actually slow.
- Fetch the viewer's saved items on every request. It's a lookup by user ID, it's cheap, and it's the part you can't safely share.
- Apply the permission filter to the cached IDs at request time, after the cache read. If your permission scopes are coarse enough to enumerate, say a tenant or a role group, you can instead put the scope in the cache key and get sharing back within each scope.
- Read prices live, or from their own cache with a TTL in the tens of seconds, and render them into the page at request time.

Before you build any of that, measure which query is slow. An hour-long TTL hides the cost from repeat searchers, but every cache miss still pays it in full, and a cold cache after a deploy means everyone pays it at once. If the real cause is an unindexed text scan, an N+1 over the result items, or a missing limit clause, fixing it may take the page under your target without a cache at all, and the cache you do add afterwards will be defending a page that's already sound.

The narrower version is still a week's work, and it's the version you can leave running unattended.