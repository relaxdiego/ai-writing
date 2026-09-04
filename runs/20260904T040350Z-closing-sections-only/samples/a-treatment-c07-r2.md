Don't ship it keyed on search text alone: that cache will serve one user's private saved items to another user.

The key has to capture everything the page varies on, and this page varies on three things the query text doesn't mention:

- the viewer's own saved items, which differ for every user
- the viewer's permissions, which decide which public results are visible at all
- the price of each item, which changes through the day

So the first person to search "blue widgets" writes their page into the cache, and for the next hour everyone searching those words gets that person's saved list and that person's permission set. A stale price is a bug you can apologise for. Showing someone a restricted item, or another user's private list, is a data leak with the same blast radius as a broken authorisation check, and it will look exactly like one in the incident review.

The speed win is still there; it just has to sit below the personalisation. Cache the part that is genuinely shared, which is the text search over the public corpus: the ordered list of matching item IDs, keyed on the normalised query plus any sort and filter parameters. On each request you take that list, apply the viewer's permission filter, merge in their saved items, and load current prices before rendering. The cached object is a list of integers rather than a page of HTML, so it is cheap to hold and can carry a long TTL, and the expensive database work you wanted to shed is the work you have actually removed.

Two things to settle before you build it. Confirm the text search really is the slow part, by timing that query separately from the permission filter and the per-user join; if the personalisation is what's slow, this cache buys you nothing and you want an index on the saved-items join instead. Then decide what happens when an item is edited or unpublished, because the ID list will go stale: either invalidate on write, or accept a bounded window and set the TTL short enough to live with.

None of that is more than the week you budgeted. It is the same cache, with the key moved down a layer.