# Postmortem: nightly cleanup job deleted 4,200 live orders

| | |
|---|---|
| **Date of incident** | 14 August 2026 |
| **Detected** | 09:20, by a customer telephoning support |
| **Resolved** | 13:40, restore from the 01:00 backup complete |
| **Customer-visible duration** | 11h 36m (02:04 to 13:40) |
| **Data loss** | 6 orders lost changes made between 01:00 and 02:00 |
| **Status** | Cleanup job disabled since 10:35 and still disabled |

## Summary

The cleanup job did exactly what it was written to do. The meaning of the data underneath it changed three days earlier, and nothing connected that change to the job that depended on it.

The job deletes orders where `status = 'draft'` and `updated_at` is more than 90 days old. That predicate encodes an assumption that is written down nowhere: that `draft` means "a customer started an order and walked away". On 11 August a change added a new status, `pending_payment`, for orders awaiting a bank transfer. To avoid editing many call sites, the author left the database default for `status` as `'draft'` and had the payment code write `pending_payment` afterwards, as a second write. Every awaiting-transfer order therefore begins life as a draft and depends on that second write to stop being one. For 4,200 rows the second write never happened, so they sat as `draft` while genuinely waiting for money to arrive. Bank transfers routinely take longer than 90 days to be given up on, the `updated_at` clock ran out, and at 02:00 on 14 August the job deleted them.

We have not yet established which creation paths reach the payment write and which do not. Until we have, we do not know the size of the population at risk, only that it was at least 4,200 on 14 August.

## Impact

4,200 live customer orders were deleted outright; there is no soft delete on this table, so the rows were gone rather than hidden. All 4,200 were restored from the 01:00 backup, which was one hour stale at the moment of deletion. Six orders had changes made in that hour and those changes are lost. Customers who looked at their order between 02:04 and 13:40 saw it missing, with no explanation and no record of it in the application.

Restoring the rows returned them to the state that caused the deletion: all 4,200 are still `status = 'draft'` with an `updated_at` older than 90 days. If the job were re-enabled today without a change, it would delete them again tonight.

## Timeline

All times 14 August unless noted.

| Time | Event |
|---|---|
| 11 Aug | Change introducing `pending_payment` merged, reviewed by one person; the cleanup job is not mentioned in the review |
| 01:00 | Nightly backup completes |
| 02:00 | Cleanup job starts |
| 02:04 | Job finishes, logging a count of 4,200 and nothing identifying the rows |
| 09:20 | A customer telephones support asking why their order has disappeared |
| 09:55 | Support escalates to engineering |
| 10:30 | An engineer confirms the rows were deleted by the cleanup job |
| 10:35 | Cleanup job disabled |
| 13:40 | 4,200 rows restored from the 01:00 backup |

The deletion went unnoticed for 7h 16m. Once a human outside engineering knew, it took 70 minutes to reach an engineer's confirmation, then 5 minutes to stop the bleeding and 3h 5m to restore.

## Why nothing caught it

Four separate defences could each have stopped this, and each failed for its own reason.

**The review had no way to see it.** The change was reviewed by one person, and the cleanup job was not raised. This is not a reviewer error: nothing records that the `status` values have consumers outside the order code, so a reviewer would have had to already know the cleanup job existed and already know its predicate. The dependency was real and invisible.

**Staging cannot express the bug.** A staging environment exists, but it holds no orders older than 30 days. A predicate with a 90-day threshold can never fire there, against any data, ever. Testing in staging would have shown the change working correctly.

**The job has no brakes.** There is no dry-run mode, so nobody can ask what a run would delete. There is no per-row logging, so after the fact we knew only that 4,200 rows went and had to reconstruct which ones from the backup. There is no threshold check, so a run deleting a hundred times the usual volume proceeds exactly like a normal one.

**Detection depended on a customer.** Nothing alerted on the deletion count, and nothing alerted on a live order vanishing. The first signal in the system was a phone call more than seven hours later, and it arrived through a channel that took another 35 minutes to reach engineering.

## What went well

The backup was an hour old and the restore worked, which is why this is a recoverable incident rather than a permanent loss of 4,200 orders. Once an engineer had confirmed the cause at 10:30, the job was disabled five minutes later, before the next night's run.

## Before the job is re-enabled

These are gating. The job stays off until all of them are done.

1. **Fix the write, not just the query.** The awaiting-transfer status must be set in the statement that inserts the row, rather than by a follow-up write that can be missed. Identify every creation path that currently relies on the default, and correct the 4,200 restored rows so they carry the status they should have had.
2. **Stop the query depending on `status` alone.** Add an exclusion for orders that have a payment intent attached, so that a future change to the status values cannot silently widen what the job deletes.
3. **Add a dry-run mode and per-row logging.** A run must be able to report its candidate set without deleting, and a real run must log the id, status and `updated_at` of every row it removes.
4. **Add an abort threshold.** If the candidate set is far outside the normal nightly range, the job stops and alerts instead of proceeding. 4,200 rows in a job that normally removes a handful should never have run to completion unattended.

## Follow-up

5. **Soft delete this table.** Set `deleted_at` and purge separately after a holding period, so that a mistake of this kind is reversible in minutes without a restore and without losing an hour of unrelated writes.
6. **Alert on bulk deletions.** Deletion volume above a threshold should page, so detection does not depend on a customer noticing and telephoning.
7. **Give the status values a listed set of consumers.** Any change to the set of statuses, or to what an existing status means, routes to the owners of every job and query that reads them. This is the defence that would have caught the incident at review time.
8. **Give staging data old enough to trigger age-based logic**, either by seeding aged rows or by making age thresholds configurable per environment. A 90-day predicate that can never fire in a test environment is untested code.
9. **Reconcile the 6 orders** that lost changes between 01:00 and 02:00, and contact the affected customers.

## Open questions

Which order creation paths skip the `pending_payment` write is still unknown, and it determines both the true size of the exposed population and whether item 1 above is complete. We should also confirm that no other job or report reads `status = 'draft'` on the assumption that it means abandoned; the cleanup job is the one we found because it caused an incident, not because we have an inventory.