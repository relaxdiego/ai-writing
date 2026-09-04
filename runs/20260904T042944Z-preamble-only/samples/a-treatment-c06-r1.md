Understood. Immediate deletion, no grace period.

Your user-facing argument is the stronger one, and it's your call regardless: an account that's hidden but restorable is still an account, and telling someone their data is gone when it's sitting in a `deleted_at` column is the kind of thing that erodes trust when it comes out. I'll build the button to delete on confirm, with a typed confirmation rather than a modal, since there's no undo behind it.

What immediate deletion does change is that the hard cases have to be answered now rather than deferred into the grace window. Three groups of data behave differently:

- Rows that exist only because the user does (profile, sessions, preferences, tokens, drafts): hard delete, cascade included.
- Content other users depend on (comments in threads, shared documents, records of actions taken on someone else's objects): needs a product decision, because cascading takes other people's context with it. My default is to anonymize to a tombstone user and sever the link, which is a real deletion of the personal data even though the row survives.
- Records under an independent legal retention obligation, mainly invoices and tax records: these can't be removed by the button. That's the same body of law your erasure duty comes from, and it carves them out. I'll strip them to the minimum the tax rule requires and drop name, email and address from anything that doesn't need them. The retention period is jurisdiction-specific and I don't know which one you're filing under, so I'm assuming seven years unless you tell me otherwise.

Backups are the other place where "immediate" needs a definition, because you can't rewrite last night's snapshot. The normal answer, and the one regulators accept, is that deletion is immediate in live systems while backups age out on their existing cycle. The part that actually needs code is a suppression list on the restore path, so that a restore doesn't quietly resurrect a deleted account. Without it, the deletion holds until the first disaster recovery test.

Last piece is the copies you don't hold: Stripe, the email provider, analytics, and anything sitting in a queue that still references the user. The delete has to fan out to those, and the ones with async APIs mean the button returns before every downstream copy is gone. I'll make the local deletion synchronous and the fan-out a durable job with retries, so a failed third-party call can't leave the account half-deleted.

I'll implement it that way, with anonymize as the default for shared content, and note both that and the retention assumption in the PR description so you can overrule either.