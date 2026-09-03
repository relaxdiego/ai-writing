Caching the rendered page under the search text alone will serve one user's private items to another, so that version can't ship.

The page mixes three things with different audiences: public results, the viewer's own saved items, and restricted results the viewer happens to be allowed to see. Cache the whole render under "blue widget" and the next person searching "blue widget" gets whatever the first person could see, saved items included. It fails open, and it fails quietly: nothing errors, the page just shows someone else's data, and we would hear about it from a customer rather than from a test. The prices are a separate problem with the same TTL. An hour of cached HTML is an hour of quoting a price we have since changed, which turns into support tickets and possibly honoured-price arguments.

What caches cleanly is the part that is genuinely the same for everyone:

- the matching item IDs for a query, unfiltered, which is usually where the heavy database work actually sits;
- permission decisions per viewer, keyed on the viewer plus something that changes when their access changes, with a short TTL;
- nothing about price, which should be read at render time or cached in seconds rather than hours.

Each request then filters the cached ID list against the viewer's permissions, loads that viewer's saved items, and hydrates prices fresh. Repeated searches stop re-running the expensive query, the rendering cost stays, and correctness no longer depends on two users never typing the same words within an hour. This is still a week of work, and it is close to the same week.

One thing to confirm before building any of it: that the database query is what's slow. If the time is going into a permission check that runs once per result row, caching the query won't move the number much, and the fix is to batch that check instead.