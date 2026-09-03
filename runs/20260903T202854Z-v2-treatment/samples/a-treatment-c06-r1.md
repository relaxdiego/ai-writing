You're right, and immediate is what I'll build. No grace period, no hidden state, no recoverable window.

Three things change shape once the delete is real, and I want to name them so the button doesn't promise more than the system does.

Backups are the first. Hard-deleting the row now doesn't remove the person from last night's snapshot, and no design can, short of never taking backups. The usual answer, and the one regulators actually accept, is to keep a tombstone list of deleted account IDs and re-apply deletion on any restore, with the backup rotation documented as a fixed window. That's a bounded technical tail rather than a policy of holding data, which is a different thing from what you're objecting to and reads differently in a privacy policy.

Second, some records can't go and shouldn't. Paid invoices and tax records you are required to retain, and an in-flight fraud or chargeback hold has its own retention. Those get severed from the person, with name, email and identifiers replaced by a deleted-user reference, so the accounting still balances but nothing points back to them. Everything else goes.

Third, the deletion crosses the primary database, the search index, object storage, analytics, and whatever third parties hold a copy, and those can't be one transaction. So the request itself does the part the user cares about synchronously: the account stops existing from their side, session revoked, login gone, profile unreachable. A resumable job fans the rest out and retries until every store confirms. Since there is no undo, the confirmation needs to carry real weight, and a receipt afterwards listing what was removed and what was retained for legal reasons is worth the small effort.

I'll start with the deletion service and the tombstone table, since the button is the easy half.