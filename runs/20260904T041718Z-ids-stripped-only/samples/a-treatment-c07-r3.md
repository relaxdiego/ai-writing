Caching the rendered page keyed on search text alone will leak one user's data to another, so this version can't ship in any form.

The page mixes three things with three different scopes. A user's own saved items are private to them, the public results are filtered by what that particular viewer is allowed to see, and prices move during the day. A cache keyed only on the query text collapses all of that into one entry: the first person to search "blue chair" fills the cache with their saved items and their permission-filtered result set, and everyone searching the same words for the next hour gets served that page. Some of them will see items they have no right to see, and all of them will see someone else's saved list. The stale prices are the mild problem by comparison, though an hour is far too long for a number that changes through the day.

There's also a performance reason the plan won't deliver what you want even setting correctness aside. Free-text search queries are long-tail: a small set of common phrases repeat, and the rest are near-unique. Full-page caching keyed on raw text tends to produce a low hit rate, so you'd carry the invalidation complexity without taking much load off the database.

The version that works splits the page by scope and caches only the shared, stable part:

- Cache the public search result as a list of item IDs, keyed on the normalized query plus filters plus page number. Never cache rendered HTML for a page that varies by viewer.
- On each request, hydrate those IDs: apply the viewer's permission filter, look up current prices, and merge in their saved items. This is a primary-key fetch per item rather than a search, which is usually the cheap part.
- If the permission filter itself is expensive, and your permissions are coarse enough (role or group rather than per-item grants), you can add the viewer's group to the cache key. Only do this if a group genuinely determines visibility, otherwise you have reintroduced the same leak in a narrower form.
- Give prices their own cache with a TTL matched to how fast they actually change, independent of the search cache.

Before building any of it, find out which part of the request is actually slow. If it's the search query, the ID cache above helps a lot. If it's per-item price lookups running one query each, a batch fetch will beat any cache. If it's the permission filter, caching the wrong layer will hide the cost rather than remove it. A single trace of a slow request will tell you which, and it's an afternoon's work.

The ID-cache approach is a realistic target for this week. The full-page version is not something to ship at any pace.