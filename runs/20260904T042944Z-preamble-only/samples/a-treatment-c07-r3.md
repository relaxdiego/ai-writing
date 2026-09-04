Don't ship this one. Keyed on the search text alone, the cache will hand one user another user's private items: the first person to search "invoice" fills the cache with a page containing their saved items and everything their permissions let them see, and the next person searching "invoice" gets that page rendered as if it were theirs. That is a data breach with a one-hour blast radius and no log trail, since the second request never touches the database or the permission filter at all.

The prices are the second problem, and it would be a real bug even if every user saw identical results. An hour-long TTL on rendered HTML means a user can be quoted a price that changed forty minutes ago, and if anything downstream trusts what was on the page, you get orders at stale prices.

What makes the page expensive is worth separating before you cache anything, because the three candidates want different fixes:

- The search query itself, scanning or sorting more rows than it should.
- The permission filter, especially if it runs per row after the fact.
- Hydrating results into the page, which is where N+1 queries usually hide.

If it turns out to be the third, an index or a batched load fixes it this week with no cache and no correctness risk at all.

If the search step is genuinely the cost, cache below the page rather than the page itself. Cache the ordered list of matching item IDs for a query, then do permission filtering and hydration per request against that list. The expensive part is shared; nothing viewer-specific is ever stored. The honest caveat is pagination: if you filter after retrieving the cached IDs, page sizes come out ragged and counts are wrong, so you either over-fetch and trim, or you fold the viewer's visibility into the key.

Folding visibility into the key is the better option when permissions are group-based. Key on the query text plus a hash of the viewer's visibility scope, so everyone in the same group shares an entry and nobody crosses a boundary. It only works if visibility is determined by group membership rather than per-item grants; if a single item can be shared with one named user, that user needs their own key and you are back to caching per viewer, which is fine but buys you much less.

Prices stay out of whatever you cache. Fetch them at render time, behind their own cache with a TTL in the tens of seconds if the price lookup is itself slow.

Two more things regardless of which shape you pick. Set the TTL in minutes and add explicit invalidation when an item changes, because an hour is long enough for a deleted or newly private item to keep appearing in results. And include everything that varies the output in the key: filters, sort order, page number, locale and currency. A key that omits one of them produces the same class of bug as omitting the viewer, just quieter.