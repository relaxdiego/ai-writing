Fair enough — your call, and the erasure-request read is reasonable. Grace period is out; deletion is immediate and irreversible.

Three things immediate deletion forces a decision on. My defaults, say the word if you want different:

1. **Rows other users reference** — comments on their threads, messages in shared channels, audit entries. I'll hard-delete anything that's only theirs and anonymize the rest: author FK nulled, name → "Deleted user", body left where it's part of someone else's record. Deleting those outright punches holes in other people's data. If you want the bodies gone too, that's a legitimate choice and I'll do it, but it's a separate call from the button.
2. **Confirmation.** One modal, type-the-username to confirm. Not a delay — just so a misclick isn't unrecoverable, since now nothing is.
3. **Backups.** Encrypted nightlies will still contain the account until they rotate out (currently 30 days), and I can't surgically edit them. That's normal and defensible, but the privacy policy should say so, otherwise the button promises something the storage layer doesn't do.

One implementation note: some of the cascade is async (object storage, search index, downstream sync). I'll kill the account row and all sessions in the same transaction, then fan out the rest — so there's no window where a "deleted" user can still log in, even if their avatar takes a minute to disappear from the CDN.

Starting on the endpoint and the button now. I'll flag anything in the cascade that doesn't fit the anonymize-vs-delete default above rather than guessing.