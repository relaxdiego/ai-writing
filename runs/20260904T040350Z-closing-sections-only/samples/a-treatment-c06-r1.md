Agreed. I'll add the button and delete on confirm, with no hidden state and no grace period.

The grace period was quietly doing three jobs, so those move into the delete itself. The first is making irreversibility visible at the moment of the click: the user types their account email to confirm, the dialog says plainly that the data is gone and cannot be recovered, and the confirmation email goes out as part of the delete rather than after it, since afterwards there is no address left to send to. Sessions and API tokens revoke in the same transaction, so an open tab can't keep acting as an account that no longer exists.

The second is completeness. With a 30-day window there was time for a sweep to catch anything the cascade missed; now the delete has to reach everything in one pass and be safe to re-run if it dies partway through. The targets are:

- rows in our own database, including anything referencing the user by foreign key rather than owning them
- the search index and any cache holding denormalised copies of profile fields
- the object store, for avatars and uploads
- our processors: Stripe customer, email provider contact list, analytics and session-replay records
- application logs and error reports containing the email or user ID

Two places where "immediate" can't be literal, and both should be stated in the privacy policy rather than papered over. Backups are the first: I can't rewrite last night's snapshot, so the account persists in backup media until it rotates out. The standard handling is to document the rotation window and keep a suppression list of deleted account hashes that a restore checks against, so a recovery can't resurrect someone. The second is invoices and tax records, which we're required to retain for years. For those the right move is to delete the person and keep the financial record with the identifying fields stripped.

One decision I need from you, because it's a product call rather than a technical one. Messages the user sent to other people exist in those other people's accounts. My assumption is that we leave the received copies in place and show the sender as a deleted user, since deleting them would silently edit other people's history. If you want them removed too, the delete gets considerably wider and I'd want to scope it separately. I'll build against that assumption unless you say otherwise.