Your call. I'll build it as specified: one confirm step, then a hard delete with no hidden state and no restore path.

Four things I'm deciding as I go, since "immediate" has to mean something concrete at the storage layer. Say the word on any of them and I'll change it.

**Backups.** Deleting the live rows doesn't reach into snapshots, which hold a copy until their rotation expires. Nobody's product does reach into them; the accepted practice is to record the deletion and re-apply it if a restore ever happens, so the copy dies on its own schedule. I'll wire that replay list up and say plainly in the deletion copy that live data goes now and backup copies expire within the retention window. That's the honest version of immediate, and it's stronger than what the grace period would have given us.

**Billing records.** Invoices and tax records usually carry a statutory retention period that a deletion request doesn't override, and getting that wrong points the same legal risk the other way. My assumption is that we strip the personal data from invoices and keep amounts, dates, and tax identifiers. This is the one I'd want your counsel to confirm rather than mine.

**Other people's threads.** Comments and messages the user left in shared spaces belong to a conversation other people are still reading. I'm anonymising the author and keeping the text, on the reading that we're erasing the person, not deleting other users' context. If you want those rows gone too, that's a different and much larger cascade and I'd rather hear it from you before writing it.

**The confirm step.** With no undo, that dialog is the only safety left, so it re-authenticates, asks for the email typed out, states that it cannot be reversed, and cancels any active subscription in the same transaction. The confirmation email goes out at deletion time, before the address is unreachable.