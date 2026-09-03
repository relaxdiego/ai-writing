Don't ship this as described: keyed on search text alone, the cache will serve one user's private page to whoever searches those words next.

The first person to run a query populates the entry, and that entry contains their saved items and every result their permissions let them see. The next viewer gets it verbatim. That is a data leak rather than a staleness bug, and an hour is long enough for it to reach a lot of people before anyone notices, because nothing about the response looks wrong to the person receiving it. Adding the viewer's identity to the key closes the leak, but it also removes most of the reason to do this: the cache becomes per-user, the hit rate collapses to whatever fraction of people repeat their own search within the hour, and the database load you were trying to shed largely stays. Permissions also move inside the window. If someone's access is revoked or an item is unshared at 10:05, a page cached at 10:00 keeps honouring the old rules until 11:00.

Prices are a smaller problem than the leak but not a trivial one. If they change through the day, an hour-long page cache means showing figures you no longer stand behind, and you will pay for that in support load at minimum.

The workable version caches the part that is genuinely shared and expensive, which is almost never the rendered page. Split the request into three layers:

- The ranked list of matching item IDs for the query text, computed before any permission filtering. This is viewer-independent and is usually where the database time goes, so it is the thing worth caching, with a TTL in minutes rather than an hour.
- Permission filtering and saved-item state, applied per request against the cached ID list. These are cheap keyed lookups, not searches.
- Prices, read at render time or from their own short-lived cache sized to how fast they actually move.

One thing to plan for: filtering after retrieval changes how many results survive, so the cached ID list has to be longer than a page and pagination has to work off the filtered set, not the raw one. That is the main piece of real work in this approach and it is what makes it a week's job rather than an afternoon's.

Before building any of it, confirm where the time is going. "Search is slow" is consistent with a missing index, an N+1 on price or permission lookups per row, or a slow render, and a cache in front of any of those buys you less than fixing them and leaves the underlying cost in place for every miss. Worth checking too whether your query distribution is concentrated enough for a shared cache to help at all; if most searches are unique strings, even the correct version of this will sit mostly empty.