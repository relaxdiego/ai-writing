# Postmortem: nightly cleanup deleted 4,200 live orders

**Date of incident:** 14 August 2026
**Duration:** 02:00 to 13:40 (11h 40m from deletion to restore)
**Detected by:** customer phone call
**Status:** mitigated; cleanup job disabled pending the fixes below

## Summary

The nightly abandoned-draft cleanup job deleted 4,200 live customer orders. The job's selection criteria, `status = 'draft'` and `updated_at` older than 90 days, had been a reliable description of an abandoned order until 11 August, when a change made `'draft'` the database default for every newly written order and left orders awaiting a bank transfer sitting in that status. Bank transfers routinely take longer than 90 days to resolve, so live orders aged into the cleanup job's window and were hard-deleted at 02:00 on 14 August. All 4,200 rows were restored from the 01:00 backup by 13:40. Six orders lost changes made between 01:00 and 02:00 and were not recoverable from the backup.

## Impact

4,200 customer orders were absent from the system for between 9 and 11 hours. During that window customers saw their orders as missing, and any process reading those rows behaved as though the orders did not exist. Six orders were restored to a state one hour stale, losing whatever was written to them between 01:00 and 02:00; those six need individual reconciliation with the customer record and with payments.

The deletion was a hard delete against a table with no soft-delete column, so the only available recovery was a restore from the previous backup. Had the backup been six hours old rather than one, the same incident would have lost a working day of changes across the whole table rather than one hour across six rows.

## Timeline

All times are on 14 August, local.

| Time | Event |
|---|---|
| 02:00 | Cleanup job starts. |
| 02:04 | Job finishes, having deleted 4,200 rows. It logs a count and nothing else. |
| 09:20 | A customer telephones support asking why their order has disappeared. |
| 09:55 | Support escalates to engineering (35m after first report). |
| 10:30 | An engineer confirms the deletion and identifies the cleanup job (8h 26m after the deletion). |
| 10:35 | Cleanup job disabled. It remains disabled. |
| 13:40 | 4,200 rows restored from the 01:00 backup. Six orders restored to a 01:00 state. |

## What happened

The cleanup query treats `status = 'draft'` as meaning "the customer started this order and walked away", and treats 90 days of inactivity as confirmation. Neither of those meanings is written down or enforced anywhere; they live only in the query itself and in the understanding of whoever wrote it.

The change merged on 11 August introduced `pending_payment` for orders awaiting a bank transfer. Rather than update the many call sites that insert orders, the author set the database default for `status` back to `'draft'` and had the payment code write `pending_payment` afterwards. That made `'draft'` the state every order passes through on creation, and the state an order remains in wherever the subsequent update does not run. Orders awaiting a bank transfer are live, are frequently untouched for months, and now carried a status the cleanup job reads as abandoned. The 90-day threshold, which had been the safety margin, instead became the mechanism: the longer a bank transfer took, the more certain the deletion.

Two properties of the change conspired here. Moving the value into a column default put it outside the code paths a reviewer would read, and the "set it afterwards" pattern makes the intended status a second write rather than a property of the insert. A single reviewer read a diff whose visible content was about payments; nothing in it named the cleanup job, and nothing in the repository connects a writer of `status` to its readers.

## Why it was not caught

The failures compound, and each of them is independently worth fixing.

- **Staging could not have shown this.** Staging holds no orders older than 30 days, so any logic gated on a 90-day predicate is dead code there. Age-gated behaviour is currently untestable outside production.
- **The job cannot be inspected before it acts.** There is no dry-run mode, so nobody can ask what the job would delete tonight without letting it delete.
- **The job records nothing about what it deleted.** A count of 4,200 is not evidence of anything. Reconstructing the blast radius required a backup comparison rather than reading a log.
- **Nothing noticed a 4,200-row delete.** A typical night's count is presumably far smaller; nothing compares the count against an expectation or refuses to proceed when the candidate set is anomalous.
- **Detection depended on a customer.** Seven hours and sixteen minutes passed between the job finishing and the first report, and another seventy minutes between that report and engineering confirmation.
- **Deletion was irreversible in-place.** With no soft delete, the cheapest possible recovery was a backup restore with an hour of data loss attached.

## Open questions

We have not yet confirmed that all 4,200 rows were orders awaiting bank transfer. `'draft'` is now the default for every order, so the deleted set may include live orders from other paths whose status was never updated; this changes the customer communication required and should be answered from the restored data before the job is re-enabled. We also do not know what read the absent rows between 02:04 and 13:40, whether any reconciliation, notification, or fulfilment process acted on their absence, or which of the six stale orders lost customer-visible changes.

## Action items

The first two are preconditions for re-enabling the job.

1. **Delete on an explicit marker, not an inferred one.** Introduce a column that positively records abandonment, set by the code path that decides an order is abandoned, and have the cleanup job select on that. `status` is written by many paths for many reasons and cannot carry this meaning.
2. **Add a dry-run mode, per-row logging, and a volume ceiling.** The job should be runnable in a mode that reports its candidate set without deleting, should log the primary keys it deletes, and should abort rather than proceed when the candidate count exceeds an expected bound.
3. **Add soft delete to the orders table,** with a separate purge after a retention window. Recovery from a mistaken cleanup should not require a restore.
4. **Give staging aged data.** Seed or time-shift orders so that logic with 30-day, 90-day, and annual thresholds can be exercised before it reaches production.
5. **Alert on batch delete volume,** so that a job removing thousands of rows pages someone at 02:04 rather than reaching a customer at 09:20.
6. **Require consumer identification for changes to status values and column defaults.** A change that adds an enum value or alters a default should list the readers of that column in the pull request, and should have a second reviewer.
7. **Audit for the same pattern elsewhere.** Find every job and query that uses `status` or another lifecycle column as a proxy for a business state, and record what each one assumes.
8. **Reconcile the six stale orders** against payment and customer records, and contact the affected customers.