Your call, and immediate deletion is what I'll build.

On the legal point, briefly and then I'll drop it: a disclosed grace period isn't unlawful under GDPR, which gives you a month to act on an erasure request, but immediate deletion is the easier posture to defend and it matches what you're telling users the button does. No argument from me.

What "immediate" actually costs is that the delete path has to be complete on the first pass, because there's no window in which to notice we missed something. So the work is mostly an inventory: user rows and their foreign-key dependents, uploaded files in object storage, the search index, cached sessions and API tokens, and the copies sitting in third parties we've pushed data to (Stripe customer, Intercom contact, Sentry user context, the marketing list). I'll enumerate those against the schema and the integrations list and delete or issue an erasure call for each in one transaction-plus-retries flow, so a partial failure is visible rather than silent.

Two places where "immediate" can't be literal, and I want the privacy policy to say so rather than have us quietly not do it. Encrypted backup snapshots can't be surgically edited, so the account persists there until the rotation window expires; the standard handling is to document that window and keep a suppression list of deleted user IDs so a restore doesn't resurrect the account. And a few records have to survive on legal grounds rather than convenience: paid invoices carry a tax retention obligation, and abuse or fraud records are the other usual carve-out. I'll reduce those to the minimum fields the obligation actually requires and strip the rest.

The one thing I need from you before I can finish is what happens to the user's visible content and their org memberships:

- Posts, comments and shared documents: hard delete them, or keep them attached to a "deleted user" tombstone so threads don't collapse?
- Files shared into a team workspace that others are actively using: same question, and it's the case most likely to generate support tickets.
- A user who is the sole admin of an org with other members still in it: delete anyway and orphan the org, block the deletion until they transfer ownership, or promote someone automatically?

I'll build the account-level deletion, the confirmation step (typed email rather than a delay, since the point is catching a misclick, not stalling), and the third-party erasure calls in the meantime, and wire in whichever content behaviour you pick. Support should also know up front that this is genuinely unrecoverable, because they'll be the ones fielding the first person who deletes by mistake.