---
id: d03
register: document
name: Architecture decision record
---
Write an architecture decision record for the following decision.

We are replacing our hand-rolled background job runner with a queue. We evaluated Celery with Redis, RQ, and Postgres-backed queueing via SKIP LOCKED. We chose Postgres SKIP LOCKED.

Reasons that mattered: we already operate Postgres and did not want to add Redis to the on-call surface; our job volume is modest (about 30,000 jobs a day, peak 40 per second); we need jobs to commit atomically with the database writes that enqueue them, which a separate broker cannot give us without an outbox; and the team has no Celery experience.

Costs we accepted: Postgres queueing does not scale past roughly a few hundred jobs per second, we must write our own retry and scheduling logic (about 400 lines), and long-running jobs hold a connection from the pool.

Status: accepted, implemented in Q3.
