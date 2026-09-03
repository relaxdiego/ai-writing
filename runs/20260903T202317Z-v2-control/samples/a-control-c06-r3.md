Agreed — that's your call and the reasoning holds up. I'll make the deletion immediate and hard: button, confirmation step (typed confirmation, not a delay), endpoint that drops the account row and all owned records in one transaction, session invalidation, and a log entry that records only that a deletion occurred and when.

Two things that still need decisions, neither of which is a grace period in disguise:

1. **Authored content others can see** — comments, shared docs, anything referenced by another user's data. Cascade-delete it, or strip the author link and keep the content? This changes the schema work meaningfully, so tell me which and I'll build it that way. Default if you don't care: cascade-delete.
2. **Backups** — the live database purge is immediate, but nightly snapshots keep a copy until they rotate out. That's a retention-window fact, not a policy choice; worth a line in the privacy policy stating the window.

I'll start on the button, endpoint, and account/profile teardown now, since those don't depend on (1).