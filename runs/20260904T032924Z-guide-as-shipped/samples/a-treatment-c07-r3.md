Don't ship this as described: keyed on search text alone, the cache serves one user's page to another and hands people items they aren't permitted to see.

The page isn't a function of the search text. It's a function of the search text plus who is asking plus what the prices are right now. Three things vary per request:

- the viewer's own saved items, which are theirs alone;
- the permission filter, which decides which public results that specific viewer may see;
- prices, which move through the day.

A cache key that captures only the first of those will happily return a page built for someone else. The first person to search "invoice" writes their page into the cache, and for the next hour everyone searching "invoice" gets it: their saved items, and the subset of results that *their* permissions allowed. This isn't stale data, it's an access-control failure wearing a cache's clothes. There's no error and no exception, just wrong content served at high speed, so it can run for weeks before someone notices their colleague's saved items on their own screen. If any of the filtered items are confidential, that's a disclosure incident with a hit-rate-shaped blast radius.

The version of this that works is to cache the part that genuinely is shared, which is the expensive database work. For a normalised query string, cache the candidate set of public result IDs and nothing else, with no per-viewer content in the value. On each request you take that cached ID list, apply the permission filter, merge in the viewer's saved items, and read prices at render time. You keep the load off the database because the search query is the part that's costly, and the per-request work is a permission check and a couple of lookups by primary key. An hour TTL on that ID list is a real decision but a smaller one: it means a newly published item takes up to an hour to appear in results, which is usually fine and is easy to explain.

The alternative, keying the whole page on search text plus viewer identity, is safe but mostly useless. Search text varies enormously per person, so the hit rate collapses and you've bought cache infrastructure that rarely fires. It also needs the key to include a version of the viewer's permission set, or revoking someone's access leaves them a working cached page for the rest of the hour.

Prices deserve their own answer before you cache anything containing them. If a displayed price is binding at checkout, an hour of drift is a commercial problem rather than a technical one. Reading prices live at render keeps that question closed.

One thing to settle before building any of this: find out what's actually slow. If the search query is missing an index, or the permission filter is doing a query per row, a cache in front of it hides a problem that returns the moment the hit rate dips, and it will dip on exactly the unusual queries that are slowest. An afternoon with the query plan and a timing breakdown tells you whether you're caching to avoid work or caching to avoid a fix, and the ID-list cache above is a week's work either way.