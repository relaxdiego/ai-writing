Agreed, we'll make it immediate.

You're right that the grace period is the part users resent, and a 30-day hold is hard to defend to someone who asked you to erase their data today. I'll wire the button to a synchronous delete: confirm, revoke sessions, delete the row and its owned records in one transaction, and return the user to a signed-out state that reflects the account is gone.

Three things can't be synchronous, and I'd rather name them now than have them surface as a broken promise later:

- **Backups.** Nightly snapshots will still contain the account until they age out of the retention window. The accepted practice is to let them expire and never restore a deleted account from one, and that's what I'll document alongside the endpoint. Rewriting backups on demand isn't feasible.
- **Downstream copies.** Anything we've pushed to analytics, email, billing, or search needs its own deletion call, and those complete on their own schedules. I'll fire them from the same handler and log failures loudly, because a silent failure there is the case where we've told someone their data is gone and it isn't.
- **Records we're required to keep.** Invoices and tax records have a statutory retention period that survives a deletion request, and abuse blocks need to keep something so a banned user can't reset by deleting and re-registering. For both, deletion means stripping them down to what the obligation requires rather than keeping the account.

On the irreversibility: since there's no window to undo a mistake, the confirmation carries the whole weight. I'll require re-authentication and typing the account email, and state plainly in the dialog that this cannot be undone and no copy is retained. That's a guard against a misclick rather than a hold on the data, so it doesn't reintroduce what you objected to.