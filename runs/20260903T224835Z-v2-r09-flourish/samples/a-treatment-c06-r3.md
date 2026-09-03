Agreed, immediate it is. I'll add the button and delete on the request.

Mechanically that means the click revokes sessions and tokens straight away, so the account is unusable the moment they confirm, and the row and blob deletion runs in a durable job that retries on failure rather than a single web request that can die halfway through and leave the account in a half-erased state. The only thing I'll put in front of the button is a re-auth or typed confirmation, which is about the click being accidental rather than about holding the data.

Three things won't be gone the instant the job finishes, and they're worth naming in the policy text next to the button so the promise you're making is one the system actually keeps:

- Encrypted backups. You can't surgically remove a row from a snapshot. The usual approach is to let backups age out on their existing retention and suppress deleted accounts on any restore, which is also what regulators expect rather than a literal instant purge.
- Invoices and tax records. Financial record-keeping law requires holding these for years, so I'll strip the personal data out of them and keep the transaction keyed to a tombstone id.
- Content sitting in other people's spaces: messages in shared threads, comments on other users' posts. Hard-deleting these rewrites conversations the other participants took part in and can make threads incoherent.

The first two I'll implement as described. On the third I'll default to reattributing to a deleted user placeholder and removing the personal data behind it, since that keeps the deletion promise for the person leaving without silently editing everyone else's history; if you'd rather it hard-delete, that's a one-line change in the cascade and I'll make it.