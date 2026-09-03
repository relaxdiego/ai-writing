Don't cache the rendered page keyed on search text. That key doesn't include the viewer, and the page is viewer-specific, so the first person to search "invoice" would have their saved items and their permission-filtered results served to the next person who searches the same word, for the rest of the hour. That is a data leak, not a slow page.

The trouble is that the page glues together three things with three different scopes, and a single cache entry has to pick one:

| Part of the page | Varies by | Safe key | Reasonable lifetime |
|---|---|---|---|
| Public search results | query text | query text | an hour is fine |
| Permission filtering | viewer's access rights | viewer, plus a version stamp on their permissions | must reflect grants and revocations quickly |
| Viewer's saved items | user | user id | invalidate on write |
| Prices | time of day | not cacheable at page level | shorter than your price update interval |

Keying on query text alone is correct for exactly one of those rows.

What I'd cache instead is the part that is genuinely shared: the query text maps to an ordered list of candidate item IDs from the public, searchable set, and that lookup is almost certainly where the database time goes. Cache that list for an hour. Then on every request, take the IDs, apply the permission filter, hydrate current prices, and merge in the viewer's own saved items. The expensive full-text work is cached, and everything that depends on who is asking or what time it is stays live. As a bonus the hit rate is better than a page cache would give you, because one entry serves every user searching those words rather than fragmenting per viewer.

Two things worth checking before you build even that. Confirm where the time actually goes: if the cost is an N+1 in hydration or a missing index, a cache hides it on hits and leaves every miss exactly as slow as today. And look at the distribution of your search strings, because free-text queries have a long tail, and if most searches are near-unique the hit rate on any query-keyed cache will be low enough that the caching is not the fix.

The ID-list cache is about the same amount of work as the page cache you described, so the week is still realistic. Three things to get right while building it: run the permission check after the cache read and never before, invalidate the ID list when items are published, unpublished or deleted, and if any of this lands at the HTTP layer, mark the logged-in page `private`/`no-store` so a CDN or shared proxy doesn't reintroduce the leak you just designed out.