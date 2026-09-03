Your call. I'll add the button and make the delete immediate and irreversible.

Two things that aren't the grace period in disguise, but that immediate deletion forces you to decide now:

- **Where the data actually lives.** Dropping the rows doesn't touch backups, read replicas, log lines, or anything already shipped to analytics and other processors. Immediate deletion means firing deletion requests at those too, and accepting that encrypted backups age out on their own schedule rather than vanishing on the button press. Worth stating that honestly in the confirmation text rather than promising a completeness you can't deliver.
- **Records you're required to keep.** Invoices, tax records, and chargeback evidence generally have to survive the account. That carve-out should be narrow, named, and on its own retention clock, not a soft version of the thing you just rejected.
- **Content other people can see.** Comments, shared documents, and sole-ownership of a team or org all need a rule: anonymise, hard-delete, or block the deletion until ownership transfers. Right now there's no answer and the delete will either orphan things or fail halfway.
- **The confirmation carries all the weight.** With no undo window, the only protection against a mis-click or a hijacked session is the dialog: re-authenticate, type the account name, state plainly that it cannot be reversed. Send the confirmation email before the address is gone, since afterwards you have no way to reach them.

I'll write it with a single transactional delete path so a partial failure rolls back rather than leaving a half-erased account.