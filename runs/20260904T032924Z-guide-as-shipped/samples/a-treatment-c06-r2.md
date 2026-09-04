Agreed. I'll make it immediate and drop the grace period.

The thing the 30-day window was quietly doing was absorbing mistakes, so removing it means a few decisions have to be made deliberately rather than by default. I'll require a password or a freshly re-authenticated session at the button: with no undo, a stolen session now permanently destroys an account instead of being recoverable, and that's the one piece of friction worth keeping. The deletion itself will run as an idempotent, resumable job rather than inside the request, since it spans several tables and the object store, but the session is invalidated and the account is gone from the user's point of view the moment they confirm.

Three categories can't simply be dropped on confirm, and here's how I'll handle each:

- **Backups.** The nightly snapshots are immutable and age out on their own retention schedule; a delete can't reach into them. So the confirmation copy will say the data is erased now and that residual copies in backups expire within the retention window, rather than claiming a completeness we don't have.
- **Invoices and tax records.** Retained, because we're required to keep them, and keyed to a customer number with the profile fields stripped rather than to the user row.
- **Content other people can still see.** Messages they sent, comments on shared documents. My default is to keep the content and replace the author with a deleted-user placeholder, because hard-deleting it also removes a copy that belongs to someone else's conversation.

That last one is the real fork, and it's a product call rather than a technical one: some teams do destroy outbound messages on deletion, and if that's what you want here, tell me and I'll wire it that way. Otherwise I'm building it with the placeholder behaviour, immediate hard delete of everything else, and re-auth on the button.