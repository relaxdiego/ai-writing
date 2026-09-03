Fair enough — that's your call, and the reasoning holds up. Immediate it is.

How I'll build it: the button opens a confirm dialog (type-your-username or re-enter password, so it can't be a misclick), then a single transactional delete that removes the account row and cascades to everything owned by it, plus queued deletion calls to any third-party processors that hold user data. The user is logged out and all their sessions/tokens are revoked in the same transaction.

Two things I want to flag before I start, not as objections but because they affect what we can truthfully say on the button:

- **Backups.** Encrypted backups roll off on their own retention schedule; we can't surgically excise one user from a snapshot without breaking its integrity. Standard practice, and GDPR accepts it, but it means the honest wording is "deleted immediately from our live systems; residual copies in encrypted backups expire within N days" rather than a flat "erased everywhere instantly." I'll use whatever N your backup retention actually is — tell me, or I'll read it off the backup config.
- **Records we may be required to keep.** Payment/invoice records usually have a statutory retention period independent of deletion requests. If you'd rather delete those too, say so and I will, but I'd want that to be a deliberate choice rather than something I did silently.

Everything else goes. Point me at the repo and I'll wire it up — I'll need to know which tables have user-owned rows without a proper cascading FK, since those are the ones that leave orphans.