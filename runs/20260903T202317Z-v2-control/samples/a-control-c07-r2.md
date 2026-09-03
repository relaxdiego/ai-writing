Caching is the right instinct, but the key is wrong in a way that will leak data.

**The page isn't a function of the search text.** It's a function of (search text, who's asking, what they're allowed to see, and the current time). Key on the text alone and the first person to search "blue chair" fills the cache with *their* saved items and *their* permission-filtered results — and everyone else who searches those words for the next hour gets that page. That's not stale data, it's one user seeing another user's private items. It'll be found by a customer, not by us.

The price staleness is a real but separate problem: an hour-old price on a live page is a support ticket at best and a pricing dispute at worst.

## What I'd ship instead, same week

Split the page by who it varies for, and cache only the part that's shared:

1. **Cache the candidate ID list for public results**, keyed on the *normalized full query* — text, filters, sort, page number, locale — not just the raw text. This is viewer-independent, so it's safe to share.
2. **Run the permission filter per request**, on every read, against that cached ID list. Never cache post-filter output. This also means a revoked permission takes effect immediately rather than at TTL expiry.
3. **Don't cache saved items**, or cache them under a key that includes the user ID with a short TTL. They're one cheap indexed lookup per user, and they're the part most likely to look broken when stale.
4. **Read prices at render time**, or cache them separately at 30–60 seconds. They're small and shared across viewers, so a short TTL still gets you most of the benefit.
5. **Start the ID-list TTL at ~5 minutes**, not an hour, and watch the hit rate. You can always raise it; lowering it after users notice missing new listings is the harder conversation.

## One thing worth checking first

Do we know *why* it's slow? Search traffic has a long tail — if most queries are unique, the hit rate will be low and the miss path is still the slow path, just now with a cold cache after every deploy. If the real cause is a missing index or an N+1 hydrating results, an afternoon of query work beats a week of cache plumbing and doesn't add an invalidation surface.

If you can point me at the search endpoint and a slow-query sample, I'll dig into where the time actually goes before we commit to the caching design.