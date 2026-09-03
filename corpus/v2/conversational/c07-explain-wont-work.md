---
id: c07
register: conversational
name: Explaining why a proposed approach will not work
---
A user proposes the following. Write your reply.

"Our search page is slow. Let's just cache everything. Put the whole search results page in the cache for an hour, keyed on the search text. If someone searches for the same words within the hour they get the cached page instantly. That should take the load off the database and we can ship it this week."

For context, the search page shows each user their own saved items alongside public results, results are filtered by whether the viewer is allowed to see each item, and prices shown on the page change through the day.
