---
id: c04
register: conversational
name: Design tradeoff question
---
We're deciding whether to store our audit log in the same Postgres database as application data, or ship it to a separate append-only store. The team is split. Volume is roughly 2 million events a day, retention is seven years for compliance, and we occasionally need to join audit events against user records for support investigations. Which way would you go and why?
