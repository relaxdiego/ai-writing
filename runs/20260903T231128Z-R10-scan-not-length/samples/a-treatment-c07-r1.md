Don't cache the rendered page keyed on search text alone: the first person to search "invoice" will fill the cache with their own saved items, and the next person searching the same word gets that page back, including items they have no permission to see. That is a data leak, not a slow page.

The trouble is that one HTML page is carrying three things with different audiences and different lifetimes:

- The ranked list of items matching the search text. Shared by everyone, changes only when the corpus changes.
- The viewer's own saved items and the permission filter over public results. Different for every viewer, and changes the moment a share is revoked.
- Prices. Same for everyone, but stale within minutes rather than an hour.

A cache key of "search text" is only correct for the first of those. So cache that one and leave the rest live. Have the search backend return the ordered list of matching item IDs for a query, cache that keyed on the normalised query text, and then per request load those items, apply the viewer's permission filter, merge in their saved items, and read current prices. The expensive full-text scan happens once per distinct query; the remaining work is primary-key lookups, which is the cheap kind of database load. An hour is a reasonable TTL for that ID list, and a stale ID that the viewer can't see gets dropped by the permission filter anyway rather than shown.

Worth confirming before you build it: check whether the text search is actually what's slow. If the profile says the time goes on per-item permission checks or price lookups issued one row at a time, then an ID-list cache buys you very little, and the fix is batching those lookups instead. The page cache as proposed wouldn't have helped there either; it would have hidden the problem behind a hit rate that collapses as soon as queries spread out across distinct phrasings.

If you do want to cache rendered output, the key has to include the viewer and something that changes when their permissions change, such as a per-user permissions version number you bump on any share or revoke, and the TTL has to come down to whatever staleness you'll accept in a price. That is a much smaller win, because the hit rate is now per user rather than global, and it is more machinery than the ID-list cache. I'd ship the ID-list version this week and measure again.