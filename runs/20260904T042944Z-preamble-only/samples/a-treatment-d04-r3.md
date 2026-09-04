# Postmortem: cleanup job deleted 4,200 live orders

**Date of incident:** 14 August 2026
**Severity:** SEV-1 (irreversible data loss on customer-facing records)
**Status:** mitigated; cleanup job disabled pending remediation
**Author:** Mark Maglana

## Summary

The nightly draft-cleanup job deleted 4,200 live customer orders that were awaiting bank transfer. A change merged on 11 August introduced a new order status, `pending_payment`, but implemented it by leaving `'draft'` as the database default and having the payment code overwrite the status after insert. Any row that came to rest as `'draft'` for the new reason was indistinguishable from an abandoned draft, and because bank transfers routinely stay open past the job's 90-day abandonment window, those rows matched the deletion query. The job ran at 02:00 on 14 August and finished at 02:04. Nobody at the company noticed. A customer telephoned support at 09:20 to ask where their order had gone.

## Impact

4,200 orders were deleted and were unavailable to customers for 11 hours and 36 minutes, from 02:04 until the restore completed at 13:40. Restoring from the 01:00 backup recovered the rows but discarded any writes made between 01:00 and 02:00, which affected 6 orders; those changes are permanently lost and each of those 6 orders needs individual reconciliation with the customer. At least one customer experienced the outage directly as a vanished order and had to initiate contact themselves, so the customer-facing cost is not bounded by the support ticket count.

## Timeline

All times are on 14 August 2026 unless stated.

| Time | Event |
| --- | --- |
| 11 Aug | Change introducing `pending_payment` is merged after review by one person |
| 02:00 | Nightly cleanup job starts |
| 02:04 | Job finishes; 4,200 rows deleted; only the count is logged |
| 09:20 | A customer telephones support to report a missing order |
| 09:55 | Support escalates to engineering (35 min triage) |
| 10:30 | Engineer confirms mass deletion (35 min investigation) |
| 10:35 | Cleanup job disabled |
| 13:40 | Rows restored from the 01:00 backup; 6 orders lose an hour of changes |

Time from deletion to any internal awareness: 7 hours 16 minutes. Time from customer report to confirmed diagnosis: 1 hour 10 minutes. Time from diagnosis to restore: 3 hours 10 minutes.

## Root cause

The cleanup query encodes an assumption that `status = 'draft'` means "a draft the customer abandoned". The 11 August change invalidated that assumption without touching the query. To avoid updating every call site that reads the column, the author kept `'draft'` as the column default and had the payment path set `pending_payment` after the row was written. That makes `'draft'` the resting state for two entirely different things: an abandoned draft, and a live order whose status the payment path has not set. No consumer of the column can tell them apart, because the only distinguishing information is which code path wrote the row.

The 90-day threshold supplied the timing. Bank transfers stay open far longer than the abandonment window the job was built around, and nothing touches an awaiting-payment order while it waits, so `updated_at` sits at its creation value and drifts past the threshold on its own. Awaiting-payment rows were not merely capable of matching the deletion query; given enough time they were certain to.

## Open question on the mechanism

The account above does not yet explain the row count, and this needs to be closed before the job is re-enabled. Rows deleted on 14 August had `updated_at` earlier than roughly 16 May, which is nearly three months before the 11 August merge. For 4,200 such rows to be carrying `status = 'draft'`, something must have written that value to pre-existing awaiting-payment orders without advancing `updated_at`. The leading hypothesis is that the migration accompanying the change normalised existing rows to the new column default at the database level, bypassing whatever sets `updated_at` in the application. Until someone reads the migration and confirms this, the blast radius is not fully characterised, and we cannot rule out a second population of affected rows.

Two further facts need verifying against the restore: whether the 13:40 restore returned only the 4,200 live orders or the whole table, and if the whole table, how many genuinely abandoned drafts are now present that should not be. The cleanup job being disabled means that backlog is still growing.

## Contributing factors

The single change is the trigger, but the incident required several standing conditions to reach this severity.

- **The job has no dry-run mode and logs only a count.** Had it logged the IDs it intended to delete, the 4,200-row set would have been reviewable before execution and identifiable afterwards without a database forensics exercise.
- **There is no volume guard.** A job whose normal output is a modest number of abandoned drafts deleted 4,200 rows in one run and did not stop or alert.
- **There is no soft delete on this table.** Recovery required a full backup restore, which is what imposed the hour-wide data loss window on the 6 affected orders.
- **There is no monitoring on order disappearance.** Detection was by a customer, seven hours after the fact, by telephone. Nothing in our own systems observed a 4,200-row drop.
- **The review did not consider consumers of the column.** One reviewer approved a change to the semantics of `orders.status`, and the cleanup job, which is the most destructive reader of that column, was not raised.
- **Staging could not have caught this.** The environment holds no orders older than 30 days, so an interaction that depends on a 90-day threshold is structurally invisible there.

## What went well

Once an engineer was looking at it, diagnosis took 35 minutes and the job was disabled 5 minutes later. The 01:00 backup existed, was current, and restored cleanly.

## Action items

Owners are unassigned pending review of this document.

| # | Action | Addresses | Priority |
| --- | --- | --- | --- |
| 1 | Confirm the migration's effect on existing rows and re-characterise the blast radius | Open question above | P0 |
| 2 | Reconcile the 6 orders with lost writes directly with the affected customers | Permanent data loss | P0 |
| 3 | Remove the two-step write: set `pending_payment` in the insert, and add a constraint forbidding payment orders from resting as `'draft'` | Root cause | P0 |
| 4 | Add soft delete to the orders table and convert the cleanup job to use it | Recovery cost | P0 |
| 5 | Add a dry-run mode and per-row ID logging to the cleanup job, retained for 30 days | No audit trail | P1 |
| 6 | Add an abort-and-alert guard when a cleanup run exceeds a threshold relative to its trailing median | No volume guard | P1 |
| 7 | Alert on unexpected drops in live order count | Seven-hour detection gap | P1 |
| 8 | Make the deletable set an exhaustive classification over all status values, so adding a status fails to compile until it is classified | Recurrence of the same class of bug | P1 |
| 9 | Seed staging with data aged across every threshold the batch jobs depend on | Staging blind spot | P2 |
| 10 | Require consumer analysis in review for changes to `orders.status`, with the destructive readers listed in the schema documentation | Review gap | P2 |

The cleanup job stays disabled until items 1, 3, 4, 5, 6 and 8 are complete, and its first re-enabled run is a dry run reviewed by hand.