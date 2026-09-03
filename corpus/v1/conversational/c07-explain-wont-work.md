---
id: c07
register: conversational
name: Explaining why a proposed approach will not work
---
The user has asked you to make their web application faster by "just caching all the database queries in a global dictionary, keyed by the SQL string, so repeated queries are instant." Their application runs across eight worker processes behind a load balancer, has per-user row-level authorization enforced in the query WHERE clauses, and handles about 400 writes per minute.

Write your reply to the user.
