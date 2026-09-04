Your call. I'll add the button and make the deletion immediate.

One thing about the legal point, because it changes what the button can honestly promise rather than whether we build it: the right to erasure has a carve-out for data you're independently required to keep, and invoices and payment records usually fall under tax retention rules measured in years, not days. Deleting those on request would create exposure in the other direction. So the deletion will be immediate and total for the account, profile, content, sessions, uploads and everything derived from them, and the billing rows will survive stripped to the fields the tax rule actually names, with the personal ones nulled. I'll write that list out as part of the change so you can see exactly what's left behind and say if it's more than you want.

The rest of the work is making "immediate" true in the places that don't cascade from the users row:

- Object storage for avatars and uploads, which has no foreign key to follow and needs its own delete pass.
- The search index, caches and CDN, which will otherwise keep serving a deleted profile until eviction.
- Third-party processors: the payment provider, the transactional email list, the support tool. These are API calls, some of them asynchronous, and one of them can fail after the local delete has committed.
- Application logs holding email addresses and IPs, which are handled by rotation rather than deletion.

Backups are the one place the promise has to be qualified. A backup can't be surgically rewritten, so the standard practice is that deletions age out with the backup rotation and are re-applied if we ever restore. I'll put the actual rotation window in the confirmation text so the user is told the true thing rather than a rounder one.

Since there's no grace period, the click is the last safeguard, and it should be a real one: reauthentication with password or passkey at the moment of deletion, a typed confirmation, and a deletion notice sent to the address on file so a hijacked session leaves a trace the owner sees.

I'll implement it as a synchronous transaction covering everything we own in our own database, plus a queued job for the external providers that retries and alerts on failure. The endpoint will return only after the local transaction commits, so nobody is told their account is gone before it is.