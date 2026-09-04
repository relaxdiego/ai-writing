Don't ship this as described. Keyed on the search text alone, the cache will hand one user's private page to the next user who searches the same words.

Look at what the page mixes together. The public results are the same for everybody. The saved items are specific to the viewer. The permission filter means even the public results are a different set per viewer, because each one has been trimmed to what that person is allowed to see. Cache the rendered page under the key `"invoice"` and the first person to run that search populates it with their saved items and their permitted set; for the next hour, everyone searching `invoice` reads that page. That isn't a stale-data annoyance, it's a disclosure, and it fails in the direction where you find out from a customer rather than from a monitor.

The prices have a smaller version of the same problem. An hour-old page shows an hour-old price, which is a number you may have to honour or explain.

What you can cache safely is the part that genuinely doesn't vary by viewer: the candidate match list for the search text, stored as item IDs, not as HTML. Then each request takes that ID list and does the cheap work per viewer:

- filter the IDs against the viewer's permissions
- join in that viewer's saved items
- look up current prices for what survives

Those are primary-key reads against a small set, which is the kind of query a database is fastest at. The expensive part, the full-text scan that produces the candidate list, is the part you stop repeating. You get most of the load reduction, the key stays `search_text` so the hit rate stays high, and nothing viewer-specific ever enters the cache. It is also a smaller change than the page cache, so the week is realistic.

Two things to settle before writing it. First, confirm the search query is actually where the time goes. If the slowness is really a per-item permission check running once per result, caching the ID list moves the needle very little and you'll have shipped for nothing; a trace of one slow request will tell you in an afternoon. Second, decide the TTL from how far behind the index may run, not from a round number. An hour of missing newly-added items is a product decision, and five minutes is often just as effective for load because the popular searches repeat constantly.

If you later want to cache whole pages, the key has to include the viewer and a version of their permission grants, so that access changes take effect immediately. That collapses the hit rate to per-user repeat searches and gives you an invalidation problem every time someone's group membership changes. Worth doing eventually, not worth doing this week.