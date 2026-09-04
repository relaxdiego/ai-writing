Immediate it is.

One correction on the legal premise, only so the button's copy doesn't overstate what we do: GDPR Article 17 gives a controller up to a month to act on an erasure request, so the 30-day hold was defensible rather than shaky. Immediate is also compliant and it is a stronger promise, so nothing about your decision is legally worse. It just isn't the argument for it. The argument for it is the one you gave, that a hidden-but-retained account is the thing people distrust, and I'll build to that.

For the deletion to actually be immediate rather than "immediate in the table the button can reach most easily", the handler needs to cover the whole footprint in one transaction, and the pieces are:

- Revoke sessions and API tokens first, so nothing in flight can write the account back after the delete.
- Hard delete the account and everything owned solely by it.
- Anonymize rather than delete anything another user's data depends on, such as comments on shared documents and audit entries, so we don't blow holes in other people's histories.
- Fire deletion calls to every downstream processor we've sent the data to: payment provider customer object, email provider, analytics, search index, and any CDN-cached avatars.
- Write a tombstone holding a hashed user ID and a timestamp, so we can prove the deletion happened and so a re-signup on the same address starts genuinely fresh.

Two things survive the click no matter how the handler is written, and the confirmation dialog should say so plainly instead of claiming total erasure. Encrypted backups keep the rows until they roll off the retention window, and the honest fix is to document that window and have a restore-then-re-delete step in the runbook so a restore doesn't resurrect deleted accounts. Invoices are the other one: most jurisdictions require retaining them for years, so the invoice keeps its legally required fields and loses everything else. Tell me the backup retention window and I'll put the real number in the dialog copy; until then I'll write it with a placeholder rather than a vague "for a period".

Because there is no undo now, the guard moves to the click itself. I'll gate the button behind password re-authentication plus typing the account name, and offer the data export on the confirmation screen rather than in the email afterwards, since afterwards there is nothing left to export from.