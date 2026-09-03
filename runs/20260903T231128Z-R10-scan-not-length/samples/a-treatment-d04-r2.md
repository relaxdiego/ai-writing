# Postmortem: nightly cleanup deleted 4,200 live orders

**Date of incident:** 14 August 2026
**Duration of customer impact:** 02:04 to 13:40 (11h 36m)
**Detected by:** a customer, by telephone
**Status:** resolved; cleanup job disabled pending the work below

## Summary

A nightly job that deletes abandoned draft orders deleted 4,200 orders that were live and awaiting bank transfer. All 4,200 rows were restored from the 01:00 backup by 13:40. Six orders lost changes made between 01:00 and 02:00 and have not been recovered.

The job selects on `status = 'draft'` together with an age threshold, and treats that combination as a proxy for "abandoned". A change merged on 11 August made `'draft'` the database default for a new bank-transfer flow, with the real status written by a second statement after the row was created. That made `'draft'` mean two different things: an order the customer walked away from, and an order that is very much alive and simply waiting on a slow payment rail. The cleanup query cannot tell them apart, and bank transfers routinely outlive the 90-day threshold.

## Timeline

| Time (14 Aug unless noted) | Event |
| --- | --- |
| 11 Aug | Change introducing `pending_payment` merged, reviewed by one person |
| 01:00 | Nightly backup taken (the restore point) |
| 02:00 | Cleanup job starts |
| 02:04 | Cleanup job finishes; 4,200 live orders deleted |
| 09:20 | Customer telephones support asking why their order has disappeared |
| 09:55 | Support escalates to engineering |
| 10:30 | Engineer confirms the deletion |
| 10:35 | Cleanup job disabled |
| 13:40 | All 4,200 rows restored from the 01:00 backup |

Detection took 7h 16m from the end of the deletion, and confirmation a further 70 minutes. Both intervals were bounded by a customer noticing, not by anything we run.

## Impact

4,200 orders were absent for up to 11h 36m. Any customer who looked during that window saw their order gone, and any process reading the orders table behaved as though those orders had never existed. One customer called. We do not know how many others saw the gap and did not call, and we should not assume the answer is zero.

Six orders were modified between the 01:00 backup and the 02:00 deletion, and those modifications are lost. The restored rows for those six are stale, not merely delayed, and they need to be identified and reconciled by hand.

## What went wrong

The immediate trigger was the interaction between two pieces of code that no one read together. The 11 August change chose to set the column default back to `'draft'` specifically to avoid touching many call sites, which is a reasonable instinct about blast radius at the call-site level, and it moved the blast radius somewhere the author was not looking: into the meaning of a value that a destructive batch job reads.

Underneath that is a modelling problem that predates the change. The cleanup query infers intent ("this order was abandoned") from a state that was never designed to carry that meaning. Nothing in the schema records when or whether an order was abandoned, so any new use of `'draft'` silently enrols rows in a deletion policy. The job would have been safe against this class of change if it deleted on an explicit `abandoned_at` timestamp, or if it named the statuses it considers safe to delete rather than the one it considers dead.

Several things then removed every opportunity to catch or limit the damage:

- **No dry-run and no per-row logging.** The job records a count and nothing else. When the engineer confirmed the deletion at 10:30, there was no record of which rows had gone; the restore had to work from the backup rather than from the job's own output.
- **No volume guardrail.** A run that deletes 4,200 rows is not a normal night for this job, and nothing compared the count against recent runs or refused to proceed.
- **No soft delete.** The table deletes rows outright, so recovery required a full backup restore and therefore inherited the backup's one-hour data-loss window.
- **No alerting.** Detection depended on a customer telephoning support.
- **Staging could not have shown this.** Staging holds no orders older than 30 days, so an age-dependent job cannot exercise its own predicate there. The environment is structurally incapable of reproducing this class of bug.
- **Review did not reach the consumer.** One reviewer looked at the change, and the cleanup job was not raised. The job is not an obvious dependency of a status enum unless you already know it exists.

## Open question

One thing is not yet established, and it matters for whether the affected population is bounded. Every deleted row had `updated_at` older than 90 days, so every deleted row predates the 11 August change by months. A new column default only applies to newly inserted rows, so the default alone does not explain how 4,200 pre-existing rows came to carry `status = 'draft'` without their `updated_at` moving. Something rewrote the status of old rows without touching the application's timestamp: a `NOT NULL DEFAULT` backfill performed as DDL, or a direct `UPDATE` that bypassed the ORM, are the obvious candidates. Until we know which, we cannot say whether other columns or other rows were affected by the same operation. This is the first thing to investigate.

## Action items

1. Reconcile the six orders with lost changes, and identify customers whose orders were absent during the window so support can contact them. Immediate.
2. Establish how pre-existing rows acquired `status = 'draft'` (see the open question above), and confirm no other rows or columns were touched. Immediate; blocks item 8.
3. Add soft delete to the orders table, so that a mistaken deletion is reversible without a restore and without a data-loss window.
4. Make the cleanup job log the primary key of every row it deletes, and add a dry-run mode that emits the same log without deleting.
5. Add an abort threshold to the job: refuse to run and alert if the candidate set exceeds a multiple of the trailing median.
6. Replace the status-based predicate with an explicit signal of abandonment, either an `abandoned_at` column or an allowlist of statuses the job may delete, so that adding a status defaults to safe.
7. Seed staging with aged order fixtures, so age-dependent jobs can be exercised at all.
8. Define the criteria for re-enabling the job. It is currently disabled and abandoned drafts are accumulating, which is a cost we are choosing to carry until items 4, 5 and 6 are done.
9. Add the cleanup job's owner as a required reviewer on migrations that alter the `status` column or its default.