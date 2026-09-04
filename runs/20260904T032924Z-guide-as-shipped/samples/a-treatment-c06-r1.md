Your call, and I'll build it that way: button, immediate deletion, no grace period.

On the legal point, a soft-delete window isn't automatically unlawful if it's disclosed, but you're right that it's harder to defend than simply doing what the user asked, and the argument about how it makes people feel stands on its own.

What I want to flag is where "immediate" can be literal and where it can't, because that determines what we can honestly say on the confirmation screen. Inside the request itself I can revoke every session and API token, cancel an active subscription, and hard-delete the account's own records, so the account is gone from every surface we control before the response returns. What can't happen synchronously is the fan-out to Stripe, the email provider, the search index, the analytics store, and log retention. Those go on a deletion job that retries until each one confirms, with an alert if any of them dead-letters, rather than a best-effort call we never check again. Realistically that finishes in minutes.

Backups are the one place immediate is structurally impossible: the data sits in them until they rotate. The accepted approach, and the one regulators expect, is a suppression list of deleted account IDs that any restore checks against, so a restore can't resurrect someone. I need your backup retention window to write the honest number into the privacy policy and the confirmation screen.

Some records will survive on purpose rather than by oversight, and I'd rather name them than have you discover them later:

- Invoices and payment records, which have a statutory retention period. Tell me the jurisdiction you want to size that to and I'll set it there rather than guessing at seven years.
- Content that lives in someone else's context: direct messages in the other person's inbox, comments on other people's posts, shared documents with collaborators.
- Security and audit logs, at whatever retention you already run.

In all three cases the author gets detached rather than the row dropped. Once I have the schema in front of me I'll list exactly what I'm proposing to anonymise versus delete outright, since that's the part where the answer is a judgment call and I don't want to make it silently.

The real consequence of dropping the grace period is that nothing recovers a mistake. A hijacked session, a misclick, a decision someone regrets in the morning: support will get those tickets and will genuinely be unable to do anything. That puts the entire safety net on the confirmation gate, so I'm going to spend real care there. Re-authentication rather than a session cookie, typing the account name, and a plain statement of what disappears now, what's retained and why, and that it cannot be undone.