Agreed. Immediate deletion, and I'll add the button.

On the legal point I'd put it only slightly differently: a 30-day hold is defensible under GDPR's "without undue delay" standard, but immediate erasure is unambiguously safe, and the hold is the part people resent. There's nothing here worth trading away.

In practice "immediate" means the button destroys the row in a transaction, invalidates every session and API token, and makes the profile 404 before the user sees a confirmation screen. No hidden state, no reactivation path. Because none of that can be walked back, the button gets a re-auth plus a typed confirmation naming what goes; that's the protection against a mis-click, in place of the grace period.

Three places where the word gets complicated. I'll take these defaults unless you say otherwise:

- **Backups.** The live database forgets them instantly, but nightly snapshots hold a copy until each snapshot rotates out, and deleting harder doesn't change that. The standard answer is a suppression list of deleted account IDs replayed against any restore. Default: build the suppression list, keep the existing retention window on the snapshots, state the window in the privacy policy.
- **Downstream processors.** Stripe, the email provider, analytics, and the search index each hold their own copy and each need their own delete call. Those are queued and land anywhere from seconds to a vendor's own SLA. The account is gone here regardless; propagation is what takes time.
- **Records with a statutory retention period.** Invoices and tax records are carved out of the erasure right by Art. 17(3)(b), and a fraud or abuse block is worthless if deleting an account clears it. Default: keep the invoice stripped to the legal minimum with no link back to a live account, and keep abuse blocks keyed to something other than the deleted identity.

The decision I need from you is what happens to content other people can see: comments, shared documents, audit-log entries naming the user, anything owned by a team rather than a person. Cascade-delete tears holes in other users' threads, and anonymizing leaves the text standing under "deleted user". I'm going with anonymize wherever another party is attached and hard delete for anything private to the account, which is a per-table flag I can flip before this ships.