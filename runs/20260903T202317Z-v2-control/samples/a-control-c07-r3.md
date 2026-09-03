The instinct is right — the cache key isn't.

**Keyed on search text alone, this leaks data between accounts.** The first person to search "blue chair" fills the cache with *their* page: their saved items, plus whatever the permission filter let them see. Everyone who searches those words for the next hour gets that page. Private items rendered to strangers, no error thrown, and it's easy to miss in staging where the test accounts usually all see the same things.

Adding the viewer to the key closes the leak and removes the benefit: hit rate drops to "the same user searched the same words twice within an hour," which is rare, so the database load stays where it is.

**Cache a layer instead of the page.** Roughly:

- Cache the expensive shared part — query → ranked list of candidate item IDs, keyed on normalized text + filters + page number. No identity in it, nothing permission-filtered baked in, so it's safe to share across users.
- Apply the permission filter per request, after the cache read. Over-fetch candidates, since filtering shrinks the result set and you don't want a half-empty page.
- Look up saved-item flags and prices per request. Those are cheap keyed reads, and batching them is straightforward.

**Prices are a separate problem from the leak.** If they move through the day, an hour of staleness means showing a price that's wrong by the time someone acts on it. Keep prices out of the cached layer, or give them their own short TTL you'd be comfortable defending to whoever owns pricing.

**Two things worth settling before building:**

Do we actually know the search query is the slow part? If it's a missing index or an N+1 in per-item rendering, a cache buys a modest win and permanent invalidation complexity on top of the original bug. Half a day of profiling tells us which, and it changes what to build.

What invalidates an entry — item edited, made private, unshared, deleted? An hour of a deleted item lingering may be acceptable; an hour of a newly-private item probably isn't.

**On this week:** profiling plus the shared candidate-list cache is a realistic scope if the slowness is where we're guessing. And there is one page that genuinely can be cached whole with the key you described — the logged-out search page, where the content is identical for everyone by definition. If anonymous traffic is a meaningful share of the load, that's the cheap win available immediately.