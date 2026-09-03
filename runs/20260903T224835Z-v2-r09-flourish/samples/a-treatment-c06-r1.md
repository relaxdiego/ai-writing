Agreed. I'll make the button delete immediately on confirm.

Two implementation points that shape what "immediate" can honestly claim. The first is backups: the row disappears from the live database the moment they confirm, but nightly snapshots hold a copy until they rotate out. Deleting from the snapshots isn't possible without destroying everyone else's restore point, so the honest version of the promise is that we delete on request and the last copies age out of backups within the retention window. I'll word the confirmation dialog that way rather than saying "erased everywhere", which would be false.

The second is that a few records can't simply be dropped, so I'm splitting them:

- Profile, credentials, sessions, uploads, preferences, and activity history: hard-deleted on confirm.
- Invoices and payment records: identity stripped, the financial row kept, because tax law requires retaining them for years and that isn't ours to waive.
- Rows other users can still see, such as comments on shared threads: author reassigned to a deleted-user tombstone so their threads don't break.

If you want a different line on the second category, tell me and I'll move it, but I'd rather not delete records we're statutorily obliged to hold.

Since this is irreversible with no undo window, I'll gate it behind typing the account email rather than a single click, and send a confirmation mail after the fact so an account takeover doesn't erase someone silently.