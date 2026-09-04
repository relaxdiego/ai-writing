# Postmortem: nightly cleanup job deleted 4,200 live orders

- **Date of incident:** 14 August
- **Deletion window:** 02:00 to 02:04
- **Customer-visible impact:** 02:04 to 13:40 (11h 36m) for 4,200 orders
- **Permanent data loss:** changes to 6 orders made between 01:00 and 02:00
- **Detection:** by a customer, 7h 16m after the deletion
- **Current status:** rows restored; cleanup job disabled since 10:35 and still disabled

## Summary

The nightly order-cleanup job deleted 4,200 live customer orders because a change merged on 11 August made the job's deletion predicate select rows it was never meant to touch. The job deletes abandoned drafts, selecting on `status = 'draft' AND updated_at < now() - 90 days`. The 11 August change added a `pending_payment` status for orders awaiting a bank transfer, but to avoid touching many call sites the author left the database default for `status` as `'draft'` and had the payment code write `pending_payment` after the row was created. Orders awaiting a bank transfer therefore sat in the database as drafts, and since bank transfers routinely remain outstanding for well over 90 days, those orders satisfied the cleanup predicate exactly. The two pieces of code were consistent with their own intentions and incompatible with each other, and nothing in the review, the test suite, or the staging environment connected them.

## Impact

4,200 orders were deleted outright. The job records only a count, so we cannot say from its own output how many of those were genuinely abandoned drafts that it was entitled to delete and how many were live orders awaiting payment; the restore returned all 4,200 rows regardless of which category they fell into. Reconstructing the split from the 01:00 backup is possible and is an action item below, because it determines how many customers need to be contacted.

For the 11 hours and 36 minutes between the deletion and the restore, affected customers saw their orders vanish from their account, which is what prompted the call to support. The restore came from the 01:00 backup, an hour before the deletion, so any change written to those rows between 01:00 and 02:00 was lost. Six orders are affected. Those changes cannot be recovered from any source we hold, and the customers concerned have not yet been identified or contacted.

## Timeline

| Time (14 Aug) | Event |
| --- | --- |
| 11 Aug | Change introducing `pending_payment` merged, reviewed by one person |
| 02:00 | Cleanup job starts |
| 02:04 | Cleanup job finishes, having deleted 4,200 rows |
| 09:20 | Customer telephones support asking why their order has disappeared |
| 09:55 | Support escalates to engineering (35m after the call) |
| 10:30 | Engineer confirms the deletion and identifies the cleanup job (35m after escalation) |
| 10:35 | Cleanup job disabled |
| 13:40 | Rows restored from the 01:00 backup (3h 5m after confirmation) |

## Analysis

The immediate cause is a fail-open default. `status` defaulted to the one value that made a row eligible for permanent deletion, and the value that protected the row was written afterwards by application code. Any row that had not yet reached the second write, or whose second write never happened, was deletion-eligible by default. A default should be the safest value in the column's domain, and here it was the most dangerous one. The choice was made to avoid updating call sites, which is a real cost, but it moved that cost onto a destructive background job that no one was looking at.

Underneath that sits a coupling problem that would have bitten us eventually anyway. The cleanup job does not delete orders that are abandoned; it deletes orders that are old and carry a particular status, and it treats those two things as equivalent. That equivalence was an unwritten assumption about what `'draft'` means, held by the job and not by anyone editing the status column. When a change gave `'draft'` a second meaning, the job kept applying the old one. Nothing in the codebase records that a destructive job depends on this field, so a reviewer looking at the payment change had no way to be reminded of it.

The change was reviewed by one person and the cleanup job was not raised. This is not primarily a reviewer failure: finding this defect required knowing that a nightly job elsewhere in the system reads `status`, holding the 90-day threshold in mind, and knowing that bank transfers regularly outlive it. That is three separate facts that live in three separate places, and expecting a single reviewer to assemble them under time pressure is not a control.

Staging could not have caught it. The interaction only becomes visible once a `pending_payment` order crosses 90 days of inactivity, and staging holds no orders older than 30 days. Any age-dependent defect in this system is invisible there by construction, which means our pre-production environment offers no coverage at all for the class of bug that retention and cleanup jobs produce.

Detection deserves separate attention, because every control failed. The job deleted 4,200 rows in four minutes and no alert fired, since nothing watches its delete count. No dashboard showed the drop in live orders. The job has no dry-run mode, so no one could have previewed the run, and it logs only a count, so even after the fact the deletion left no record of what it removed. The first signal came from a customer more than seven hours later, and it then took another 70 minutes to reach an engineer and be confirmed. A destructive job with no logging, no soft delete, and no volume guard is one merge away from an unrecoverable incident at any time; on 14 August we were saved by the backup schedule rather than by any deliberate protection.

## Open questions

The record does not explain why the 14 August run was the first to delete these rows. The change merged on 11 August, and the affected orders were already more than 90 days old, so the runs on 12 and 13 August should have matched them too. The likely explanation is that the merge did not reach production until 13 August, but the deploy time is not established, and neither is how awaiting-bank-transfer orders were represented before the change. Until both are confirmed we cannot rule out that earlier runs also deleted live rows, in which case the impact figure of 4,200 is too low and those rows are past the retention window of the backups we would need to restore them.

## What went well

The backup was only an hour old and the restore path worked without incident. Once an engineer had the report, diagnosis took 5 minutes and the job was disabled immediately, so no further nightly run could compound the loss.

## Action items

| Action | Class | Priority | Owner |
| --- | --- | --- | --- |
| Confirm the deploy time of the 11 Aug change and check delete counts for the 12 and 13 Aug runs against the same failure mode | Investigate | P1 | unassigned |
| Reconstruct from the 01:00 backup which of the 4,200 rows were awaiting payment, and identify the 6 orders with lost changes | Investigate | P1 | unassigned |
| Contact customers whose orders were affected, prioritising the 6 with unrecoverable changes | Mitigate | P1 | unassigned |
| Make `status` NOT NULL with no default, and set `pending_payment` in the same statement that creates the row | Prevent | P1 | unassigned |
| Audit for any live orders still carrying `'draft'` while awaiting payment, and correct them | Prevent | P1 | unassigned |
| Add a volume guard to the cleanup job: abort and alert if a run would delete more than a configured absolute count or a set margin above the trailing median | Prevent | P1 | unassigned |
| Add a dry-run mode and per-row deletion logging (id, status, updated_at), retained for at least 90 days | Detect | P1 | unassigned |
| Add soft delete to the orders table so cleanup marks rows and a separate, slower process hard-deletes them | Mitigate | P1 | unassigned |
| Re-enable the cleanup job only once the guard, logging, and soft delete are in place, after a dry run reviewed by two people | Prevent | P1 | unassigned |
| Replace status inference with an explicit eligibility marker (for example `abandoned_at`, set when an order is positively determined to be abandoned) and delete on that | Prevent | P2 | unassigned |
| Alert on unexpected drops in live order count, independent of the job's own reporting | Detect | P2 | unassigned |
| Record the consumers of `status` next to its definition, and require changes to its values or default to name them | Prevent | P2 | unassigned |
| Give staging orders spanning more than 90 days of age, or run age-dependent jobs against a sanitised production snapshot | Detect | P2 | unassigned |
| Add a support runbook entry for "customer reports an order has disappeared" that escalates directly to engineering | Detect | P3 | unassigned |