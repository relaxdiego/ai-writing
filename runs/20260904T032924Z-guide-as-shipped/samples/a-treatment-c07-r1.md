Caching is the right instinct, but not keyed on the search text alone: that key leaks one user's data to another. The page contains the viewer's own saved items and results filtered by what the viewer is allowed to see, so the key has to include the viewer's identity or the page is not a function of the key. Two people searching "blue chair" get the same cache entry, and whoever searches first decides what the second one sees, including saved items that aren't theirs and results they have no permission to view. This isn't a race condition you'd hit rarely; it's the normal path, and it holds for an hour per distinct query.

The prices are a smaller problem of the same kind. If they move through the day and people act on them, an hour-old page is an hour-old price, and you'll be arguing about which one was binding.

The way to keep the speed is to cache the part that's genuinely shared and rebuild the part that isn't. Roughly:

- **Cacheable across users:** the ranked list of candidate item IDs for a given search text. This is usually where the database time actually goes.
- **Per request, not cached:** the permission filter over those IDs, the current prices, and the viewer's saved items.
- **Cacheable per viewer, if you want a second layer:** the fully rendered page keyed on (search text, user ID), with a much shorter TTL than an hour.

Hydrating a few dozen IDs by primary key and running the permission check is cheap next to whatever the search query is doing, so you keep most of the win. If the permission model is coarse enough that viewers fall into a handful of visibility groups, you can put the group in the key and cache the filtered list too.

One thing worth doing before you spend the week: find out where the time is going. If it's an unindexed column, a missing composite index, or an N+1 on the item hydration, a cache in front of it hides the problem at current traffic and hands it back at the next step up, and you'll be debugging it through a cache layer instead of directly. A single slow-query log or an EXPLAIN on the search query will tell you in an afternoon whether you're buying a fix or a delay.

The version I'd ship is the ID-list cache with per-request permission filtering and live prices. It's the same week of work, it takes the same load off the database, and it doesn't put one customer's saved items on another customer's screen.