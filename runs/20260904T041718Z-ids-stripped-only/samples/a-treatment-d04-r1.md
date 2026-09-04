# Postmortem: Nightly cleanup job deleted 4,200 live customer orders

Status: resolved, with residual data loss. Cleanup job remains disabled.

## Summary

At 02:00 on 14 August the nightly cleanup job deleted 4,200 live customer orders. The job is intended to delete abandoned draft orders and identifies them as rows where `status = 'draft'` and `updated_at` is more than 90 days old. On 11 August a change introduced a new status, `pending_payment`, for orders awaiting a bank transfer, and implemented it by leaving the database default for `status` at `'draft'` and having the payment code write `pending_payment` afterwards. Bank transfers routinely take more than 90 days to be given up on, so orders awaiting payment accumulate age without being touched, and any of them still carrying `status = 'draft'` matched the cleanup predicate exactly. The job finished at 02:04. Nobody inside the company noticed. A customer telephoned support at 09:20 to ask where their order had gone, and the deletion was confirmed by an engineer at 10:30. The job was disabled at 10:35 and the rows were restored from the 01:00 backup by 13:40.

## Impact

4,200 live customer orders were absent from the system for eleven hours and forty minutes, between 02:00 and 13:40. Customers holding those orders could not see or act on them during that window, and at least one of them called support about it; the true number of customers who noticed is not known, because there is no record of failed lookups against the deleted rows.

Six orders lost the changes made to them between 01:00 and 02:00, which is the gap between the backup and the deletion. That loss is permanent. Those six orders need to be identified from the restore and their customers contacted, because the system now presents an hour-old version of each as if it were current.

## Timeline

All times on 14 August unless stated.

| Time | Event |
| --- | --- |
| 11 Aug | Change introducing `pending_payment` merged, reviewed by one person |
| 02:00 | Cleanup job starts |
| 02:04 | Job finishes, having deleted 4,200 live orders |
| 09:20 | Customer telephones support asking why their order has disappeared |
| 09:55 | Support escalates to engineering |
| 10:30 | Engineer confirms the deletion |
| 10:35 | Cleanup job disabled |
| 13:40 | Rows restored from the 01:00 backup |

Detection took seven hours and twenty minutes from the deletion, and depended entirely on a customer picking up the phone. A further seventy minutes passed between that call and engineering confirming what had happened.

## What went wrong

The cleanup query encodes a definition of "abandoned" that nothing in the system enforces or records: an order is abandoned if it is a draft and has not been touched for 90 days. That definition was correct while `'draft'` meant only "not yet submitted". The `pending_payment` change made `'draft'` also the state a bank-transfer order passes through on its way to being live, and did so by way of the column default, so the value is written by the database on every insert rather than by code a reader would encounter. From the cleanup job's side nothing changed, which is precisely the problem: the query kept returning rows under a rule that had stopped being true.

The implementation choice that made this reachable was writing the row first and setting `pending_payment` in a second step, adopted to avoid touching many call sites. That leaves a window, and any failure in the second step leaves the row permanently in `'draft'` with no indication that it is anything other than an ordinary abandoned draft. We have not yet established why the 4,200 deleted rows still carried `'draft'` rather than `pending_payment`, and this postmortem does not assert an answer. The restored rows are available and should settle it. This matters for the remediation: if the rows were mid-transition, the fix is atomicity; if the second write failed silently, the fix is error handling and a reconciliation check; if the transition never applied to older bank-transfer orders at all, the fix is a backfill. Determining which is the first action item below.

Three things stood between that bug and 4,200 deletions, and none of them held.

- Review did not surface the cleanup job. One reviewer looked at a change that redefined the meaning of a column value, and there is no mechanism that lists the existing consumers of `status` for a reviewer to check. The cleanup job was not mentioned.
- Staging could not have caught it. The environment holds no orders older than 30 days, so a predicate keyed on 90 days matches nothing there. Any test of this job in staging is guaranteed to pass and guaranteed to be meaningless.
- The job itself has no safety properties. There is no dry-run mode, no per-row logging, no soft delete on the table, and no check on the volume of rows a single run removes. A destructive job that deletes 4,200 rows on a night it normally deletes far fewer had nothing to make it stop or say what it had done.

The absence of logging also lengthened the incident. The job records a count and nothing else, so when the engineer confirmed the deletion at 10:30 there was no list of what had been deleted; recovery required restoring from backup rather than reinstating a known set of rows, and it is the restore, not any log, that tells us the deletion touched 4,200 records.

## What went well

Once the report reached an engineer, diagnosis and containment were quick: thirty-five minutes to confirm, five more to disable the job. The 01:00 backup existed, was current, and restored cleanly, which held permanent loss to six orders out of 4,200.

## Current state and ongoing risk

The cleanup job is disabled and must stay disabled. The restore put the 4,200 rows back in the state that matches the cleanup predicate, so re-enabling the job before the query is fixed would delete them again. Meanwhile genuinely abandoned drafts are accumulating unremoved, which is a cost we are choosing to carry for now and should be tracked so it does not become a second incident.

## Action items

Correctness of the fix, in priority order:

1. Determine from the restored rows why they held `status = 'draft'`, and record the finding. Everything below assumes a specific answer to this and should be revisited if the answer surprises us.
2. Make the cleanup query name the states it deletes explicitly and exclude every other state, rather than treating `'draft'` as a proxy for abandonment. A new status value should not be able to silently join the deletion set.
3. Remove the two-step state assignment for bank-transfer orders, so that a row is never persisted in a state that misrepresents it. If the write and the update cannot be made atomic, add a reconciliation job that finds and reports rows stuck in `'draft'` with a payment attached.

Safety of destructive jobs, which would have limited this incident regardless of the bug:

4. Add a dry-run mode to the cleanup job and require its output to be reviewed before any change to its predicate ships.
5. Log the identifier of every row the job deletes, not just a count.
6. Add an abort threshold: if a single run selects more rows than a defined ceiling, the job stops without deleting and alerts.
7. Introduce soft delete on this table so that recovery does not require a backup restore and does not cost an hour of unrelated writes.

Detection and process:

8. Alert on the cleanup job's deletion count so that an anomalous run is known within minutes rather than at the next customer call.
9. Give staging data that spans the ages the production predicates test against, or accept explicitly that age-based jobs are untestable there and require the dry-run in production instead.
10. Require a second reviewer, and an explicit check of `status` consumers, for changes that add or redefine a value in a state column.

Customer-facing:

11. Identify the six orders whose 01:00 to 02:00 changes were lost, and contact those customers. This is the only item with unrecoverable data behind it and should not wait on the engineering work.