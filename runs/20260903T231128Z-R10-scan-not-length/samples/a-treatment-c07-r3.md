Don't cache the page keyed on search text alone. With that key, the first person to search "invoice" fills the entry and everyone else searching "invoice" for the next hour is served their page, private saved items and all.

The page's content isn't a function of the query. It's a function of the query, who is viewing, what that viewer is permitted to see, and the current prices. A cache key has to contain everything the value depends on, and yours contains one of four inputs. The saved-items leak is the loudest failure, but the permission filter has the same shape and is worse: a viewer with narrow access gets a page rendered against someone else's broader access, so restricted results are shown to people who were specifically not allowed to see them. Revoking someone's access also stops meaning anything for up to an hour, which is exactly the window in which revocation matters. The stale prices are the mildest of the three, though an hour is long enough that a customer can act on a number the page no longer stands behind, and that's a decision worth making on purpose rather than inheriting from a TTL chosen for a different reason.

The instinct to cache is right; it's the granularity that's wrong. Split the page by what actually varies:

- The public candidate set for a normalised query is shared across all viewers, changes slowly, and is usually where the database time goes. Cache this, keyed on the normalised query. An hour is defensible.
- Permission filtering and the viewer's saved items are per-request. Apply them to the cached candidate set on the way out.
- Prices come from their own short-TTL cache, seconds to a couple of minutes, or are read at render time.

That still ships this week, and it keeps the expensive part of the work shared while the correctness-bearing part stays per-request.

Before building it, confirm where the time is going. If the slow part turns out to be the permission filter running per result rather than the candidate query, caching the candidate set buys you very little and the fix is an index or a bulk permission check instead. Whole-page caching is attractive partly because it doesn't require knowing the answer to that question, which is also why it tends to be the wrong instrument.

If you do end up wanting a per-viewer page cache later, the key needs the viewer id and a permissions epoch that bumps whenever their access changes, so a revocation invalidates rather than waits. Hit rates on a key that specific are usually low enough that it isn't worth the machinery.