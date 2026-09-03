Don't cache the rendered page keyed on the search text. As described, the cache will serve one user's private saved items, and results another user was filtered out of seeing, to the next person who searches the same words.

The page isn't a function of the query. It's a function of the query, the viewer's saved items, and the viewer's permissions. Key it on the query alone and the first person to search "quarterly invoice" warms the cache; everyone who searches those words for the next hour gets that person's page, including their saved items and any restricted result they were allowed to see. This isn't a staleness bug you can accept for a week and clean up later. It is a disclosure bug, and the way it usually surfaces is a customer screenshotting someone else's data.

The prices are a smaller and separate problem. An hour of staleness means quoting a price the system no longer honours, which may or may not be tolerable depending on what happens when the user clicks through and gets charged the current one. Worth deciding deliberately rather than inheriting an hour from the page TTL.

The good news is that the database load you're trying to shed almost certainly isn't in the per-viewer part. Cache the layers that genuinely are shared:

- The candidate result IDs from the search query, before any permission filtering. Identical for every viewer, safe for an hour or longer.
- Per-item display data (title, description, thumbnail) keyed by item ID, invalidated when the item is edited. Shared across every page that shows the item.
- Prices keyed by item ID with a short TTL of a minute or two, or read live if the price lookup is cheap.
- Nothing else. Permission filtering and the viewer's saved items get computed per request, against the cached ID list.

A request then does one cheap permission check over a few dozen cached IDs plus one lookup of the viewer's saved items, instead of running the full search. That is most of the load you wanted to remove, and it is roughly the same amount of work to build, so this week is still realistic.

If you're tempted to keep the whole-page cache and just add the viewer to the key, look at your hit rate first. The same user repeating the same search inside an hour is rare, so a per-viewer page cache mostly stores entries nobody reads, and you'd still have to version the key against permission changes and price updates. The shared layers are where the repetition actually is.