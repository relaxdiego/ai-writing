Don't ship it with that key. Keyed on search text alone, the cache will hand one user's rendered page to a different user, including their saved items and any result the second user isn't permitted to see. A shorter TTL doesn't fix that; it just narrows the window on a permissions bypass, and the person who finds it will be a customer looking at someone else's private item.

The trouble is that the page mixes three things that vary along different axes, and a single whole-page cache forces them all onto one key. Match results vary with the query text, saved items vary with the viewer, permission filtering varies with the viewer and the item, and prices vary with the clock. Cache the composed page and you've asserted that all four depend only on the search words.

Prices are a separate problem from the leak and survive fixing the key. An hour of stale prices on a page people buy from means the number shown and the number charged can differ, which becomes a support load and possibly a refund policy question. Invalidation is the same class of issue: for an hour after an item is deleted, unpublished, or switched to private, it keeps appearing in cached pages, so "make this private" quietly stops meaning what it says.

Before building any of this, spend half a day finding out what's actually slow. "Search is slow, so cache it" is often a missing index or an N+1 on the per-result price lookup wearing a caching problem's clothes, and if it is, you fix it in a day with no cache to reason about. Get a profile of one slow request first: time in the match query, time in permission filtering, time in price lookups, time in render.

If the match query really is the cost, cache along the axes rather than across them:

| Part of the page | Varies with | Reasonable cache |
|---|---|---|
| Match set for a query | normalized query, filters, sort, page | item IDs, 5 to 15 min |
| Permission filter | viewer and item | apply per request, not cached |
| Saved items | viewer | per-viewer key, short TTL |
| Prices | time | per item, seconds, or read live |

Two details decide whether this works. Cache IDs, not HTML, so filtering and rendering still happen per viewer. And cache a deeper candidate list than one page's worth, because if you cache the top 20 matches and then filter, a user who can't see half of them gets a ten-item page with no way to reach the rest.

If visibility is coarse rather than per-item, say public versus signed-in versus per-organisation, you can fold the scope into the key and cache further down the stack: key on (normalized query, filters, sort, page, scope). That's cheaper and simpler, and it only holds if no two viewers in the same scope can ever see different result sets. Worth confirming against the actual ACL rules before relying on it.

Whatever the key ends up being, normalize it deliberately: casing, whitespace, and synonym handling should collapse into the same entry, while filters, sort order, and page number must stay in the key or page 2 of one search will serve page 1 of another.

The match-set cache alone is shippable this week, and it's the piece carrying the database load.