Cache the page keyed on search text alone and you will serve one user's private saved items to another user.

The page's output is a function of more than the query string. Three separate things vary it:

- the viewer's own saved items, shown inline with the results
- the permission filter, which drops items this viewer isn't allowed to see
- prices, which move through the day

A key of just the search text asserts that none of those matters. In practice the first person to search "blue widget" fills the cache, and everyone searching the same words for the next hour gets that person's saved items and gets public items they may have no right to see. That is a disclosure bug rather than a staleness bug, and it surfaces as a support ticket, not as a graph. The prices are the milder version of the same error: an hour-old price on a page someone may act on.

What you can cache is the part that genuinely doesn't depend on who is asking. Run the search to produce an ordered list of candidate public item IDs, and cache that list, keyed on the normalised search text. Then per request: filter the list against the viewer's permissions, merge in their saved items, and read prices live. The expensive full-text scan gets amortised across everyone searching those words, and everything that differs by viewer is computed per viewer. If the per-request hydration turns out to be the slow half, cache item rows individually under a short TTL with price excluded from the cached row, so a popular item costs a lookup instead of a join.

Before building either layer, get one number from production: what share of the search page's database time is the scan itself versus the per-row work. Repeated identical searches are usually concentrated in a handful of head terms, so a query cache can have a hit rate low enough that it changes nothing, and the real win sits in the second layer or in an index you haven't added yet. That measurement is a day's work at most and it decides which of the two caches is worth writing.

The ID-list cache is small enough to ship this week and safe because its key covers everything its value depends on. Hold any later cache to the same test: the key has to name every input the value varies with, and viewer identity is one of those inputs here whether or not it appears in the URL.