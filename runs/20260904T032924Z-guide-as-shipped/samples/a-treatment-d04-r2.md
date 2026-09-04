# Postmortem: nightly cleanup job deleted 4,200 live orders

**Date of incident:** 14 August 2026
**Status:** resolved; cleanup job remains disabled
**Author:** Mark Maglana

## Summary

The cleanup job should stay disabled until it has a dry-run mode, per-row logging and a soft delete, because the failure was not a bad query but an unguarded one, and the same class of change will reach it again. On 14 August the nightly job ran at 02:00 and deleted 4,200 live customer orders in four minutes. The job deletes rows where `status = 'draft'` and `updated_at` is more than 90 days old, which was a correct description of an abandoned draft until 11 August, when a change made `draft` the state every order is born into rather than a state an order is deliberately left in. From that point the predicate matched orders that were alive and awaiting a bank transfer.

## Impact

4,200 orders were unavailable to customers and to internal systems from 02:04 until they were restored at 13:40, a window of 11 hours and 36 minutes. Restoration came from the 01:00 backup, so any change written between 01:00 and 02:00 was lost permanently; 6 orders were affected by that gap and need manual reconciliation with the customer. We know that at least one customer discovered the loss on their own, and we have no way to count the customers who saw a missing order and did not call.

## Timeline

All times are local. The merge on 11 August is included because it set the conditions for the run three days later.

| Time | Event |
| --- | --- |
| 11 Aug | Change merged introducing the `pending_payment` status; database default for `status` set to `'draft'` |
| 02:00 | Nightly cleanup job starts |
| 02:04 | Job finishes, having deleted 4,200 rows; logs the count only |
| 09:20 | Customer telephones support asking why their order has disappeared |
| 09:55 | Support escalates to engineering (35 min after the call) |
| 10:30 | Engineer confirms the deletion (7h 16m after it occurred) |
| 10:35 | Cleanup job disabled |
| 13:40 | Rows restored from the 01:00 backup |

## What happened

The change on 11 August introduced `pending_payment` for orders awaiting a bank transfer, which was the right modelling decision. To avoid editing the call sites that create orders, the author left the column default at `'draft'` and had the payment code write `pending_payment` after the row was inserted. This made `draft` carry two meanings at once: the state of an order a customer started and abandoned, and the state of any order whose real status has not been written yet or was never written at all. The cleanup query only ever understood the first meaning, and nothing in the schema, the code or the review process connected the two.

The second condition, `updated_at < now() - 90 days`, encodes a business assumption that ninety days of inactivity means abandonment. Bank transfers routinely sit longer than that before anyone would call them abandoned, so even a correctly-statused row would be at risk under a query written against a payment method that settles in seconds. The status defect and the threshold assumption are independent problems and both need fixing.

## Why we did not catch it

Nothing in the pipeline was positioned to see this. The reviewer looked at a status enum and a default, which is a small and self-contained change on its face; the cleanup job lives elsewhere, reads that column, and was not raised in review, and we have no index of consumers that would have surfaced it. Staging holds no orders older than 30 days, so the 90-day predicate cannot match anything there and the interaction is invisible by construction: a test environment that cannot age data cannot test a job whose only interesting behaviour is time-dependent. That left detection to a customer telephone call seven hours after the fact, and even then the deletion of 4,200 rows in one run produced no alert, no threshold breach and no anomaly anyone was watching.

## What we do not know

The job logged a count and nothing else, and the table has no soft delete, so our own records cannot tell us which 4,200 rows were deleted or what they had in common. We can reconstruct the population by querying the restored data, and that work has not been done yet. Two candidate populations fit the facts and imply different fixes: bank-transfer orders that predate the 11 August change and were never backfilled into `pending_payment`, or orders where the insert succeeded and the follow-up write to `pending_payment` did not. If the second group exists at all, the write-then-update pattern is losing status silently in normal operation and the cleanup job merely made it visible.

## What went well

The 01:00 backup existed, was current, and restored cleanly, which bounded the damage to a one-hour window and 6 orders. Once an engineer had the report, confirmation took under an hour and the job was disabled five minutes after that.

## Action items

| Action | Addresses | Priority |
| --- | --- | --- |
| Query the restored rows to establish which population was deleted and whether status updates are failing in normal operation | The unknown above; may escalate | Now |
| Reconcile the 6 orders that lost 01:00–02:00 changes with the customers affected | Permanent data loss | Now |
| Keep the cleanup job disabled until the guards below are in place | Recurrence | Now, ongoing |
| Add a soft delete to the orders table so a wrong deletion is reversible without a restore | 11-hour outage; permanent loss of the backup gap | High |
| Add a dry-run mode and per-row logging of deleted IDs to the cleanup job | Inability to characterise the blast radius after the fact | High |
| Add an abort threshold to the job: refuse to run and alert if the candidate set exceeds a configured volume | Silent 4,200-row deletion | High |
| Stop using `draft` as the column default; make the creating code state the status explicitly, or introduce a distinct initial state that no cleanup job matches | Root cause | High |
| Rewrite the cleanup predicate to select abandoned drafts positively rather than by exclusion, and exclude any status representing a live payment | Root cause; the 90-day assumption | High |
| Alert on any bulk delete against customer-facing tables, independent of the job that issued it | Detection by customer telephone call | Medium |
| Seed staging with aged data so time-dependent jobs can be exercised there | Untestable interaction | Medium |
| Record the consumers of the `status` column somewhere a reviewer will find them, and require changes to status semantics to name them | Review scope | Medium |