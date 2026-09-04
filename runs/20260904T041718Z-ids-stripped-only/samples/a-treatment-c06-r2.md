Agreed, immediate it is. Your call on the product, and the reasoning holds up: a grace period is a retention decision dressed up as a safety feature, and the person who clicked the button didn't ask for it.

One factual note before I build it, not to reopen the decision: a 30-day window isn't itself a legal problem under GDPR, which gives a controller up to a month to act on an erasure request. So the argument for immediate is the honesty one, which is the better argument anyway. Where the legal exposure actually bites is the other direction, and it shapes the implementation: some records you are required to keep. Invoices and tax records have statutory retention periods that a user's deletion request doesn't override, so those get the user's identity stripped rather than being dropped.

That's the main thing "immediate" forces us to decide up front, because there's no undo to fall back on:

- **Confirmation.** Re-authenticate and require typing the account name, not an "are you sure" dialog. This is the only guard left.
- **Rows other users can see.** Comments, shared documents, team memberships. Either they vanish and break other people's threads, or they become "deleted user." I'll go with anonymizing the author and keeping the content unless you want them gone.
- **Backups.** The encrypted nightly backups will still contain the row until they age out. Nobody can honor "immediate" down to the backup tier; the standard and defensible answer is that backups are never restored selectively into production and expire on their own schedule. We should say that in the privacy policy rather than imply the data is gone everywhere at once.
- **Downstream processors.** Stripe, the mail provider, analytics. Deletion has to fan out to each of them, and those calls can fail, so they go in a retryable queue.

Mechanically: the button revokes every session and API token synchronously and marks the account gone before the request returns, so from the user's side it is done. The cascade of hard deletes and the processor fan-out run in a job kicked off in that same request, with retries, because a Stripe timeout shouldn't leave the account half-deleted and still logged in.