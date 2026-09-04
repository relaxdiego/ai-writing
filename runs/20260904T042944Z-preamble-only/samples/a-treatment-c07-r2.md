Don't ship it keyed on the search text alone: that cache will serve one user's private saved items, and items they aren't allowed to see, to whoever searches the same words next.

The page you're caching isn't one thing. It's three, and they have different sharing properties:

- Public results for the query text. Genuinely shared between viewers, and probably where the database time actually goes.
- The viewer's own saved items. Unique per user, never shareable.
- Permission-filtered results. Same query text, different rows per viewer, so "invoice" legitimately renders a different page for two people. A cache that can't tell them apart is an access-control bug that happens to be fast.
- Prices. An hour TTL means up to an hour of wrong numbers in front of someone who may act on them.

So cache the shared layer, not the page. Have the query hit a cache keyed on the normalised search text and return only the ordered list of public result IDs, then hydrate each request from that: fetch prices fresh, run the permission filter against the viewer, and merge in the viewer's saved items on the uncached path. You keep the expensive full-text scan off the database, which is the win you were after, and nothing viewer-specific ever crosses between users. Keep that TTL in minutes rather than an hour so an edited or newly-private item doesn't linger, and invalidate on delete and visibility change rather than waiting it out.

If you do want the whole page cached, the key has to name everything the render depends on: viewer identity (or an exact permission-set fingerprint) plus a price epoch. That's correct and it's close to useless, because the hit rate collapses once every key is per-user. The splitting is what buys you both properties at once.

One thing to do before any of it: find out what's slow. If it's a missing index on the search column or an N+1 hydrating results, that's a permanent fix measured in one query plan, and a cache laid over it hides the problem while making the failure mode worse. Cold cache under load sends every concurrent request at the same slow query at once, so whatever you build needs single-flight around the fill.

The split version is still a this-week change. The database load comes off in the same place it would have, and the part you'd be rushing is the key design, which is exactly the part that has to be right.