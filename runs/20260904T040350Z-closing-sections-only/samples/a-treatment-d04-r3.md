# Postmortem: nightly cleanup job deleted 4,200 live orders

**Date of incident:** 14 August 2026
**Status:** mitigated, cleanup job disabled, root cause partially established
**Author:** Mark Maglana

## Summary

The nightly cleanup job, which deletes draft orders abandoned more than 90 days ago, deleted 4,200 rows that included live customer orders awaiting bank transfer. The job's definition of an abandoned order is `status = 'draft'`, and a change merged on 11 August made `'draft'` the database default for rows that the payment code later stamps `pending_payment`. The value stopped meaning "the customer walked away" and started also meaning "nothing has claimed this row yet", and a hard-delete query was reading it as the former.

Rows were restored from the 01:00 backup by 13:40. Six orders permanently lost changes made between 01:00 and 02:00. Detection was by a customer telephone call seven hours after the deletion; no automated signal fired.

## Impact

4,200 rows were deleted from the orders table and were unavailable to customers and to support for eleven hours and forty minutes from the start of the job. During that window, affected customers saw their orders vanish with no explanation and no support-visible record of what had happened.

Six orders lost an hour of writes that the 01:00 backup predates. That loss is permanent; there is no soft delete on this table and no write-ahead capture between backups that we can replay. Those six customers need to be contacted individually, and we should assume the lost writes include payment confirmations.

We do not know the composition of the 4,200. The job logs a count and nothing else, so we cannot say from the logs how many were genuine abandoned drafts and how many were live bank-transfer orders. See "What we still do not know" below.

## Timeline

All times UTC. Dates are 14 August 2026 unless stated.

| Time | Event |
| --- | --- |
| 11 Aug | Change introducing `pending_payment` is merged, reviewed by one person. The cleanup job is not mentioned in the review. |
| 02:00 | Nightly cleanup job starts. |
| 02:04 | Job finishes. It logs a deletion count of 4,200 and no row identifiers. No alert fires. |
| 09:20 | A customer telephones support to ask why their order has disappeared. |
| 09:55 | Support escalates to engineering, 35 minutes after the call. |
| 10:30 | An engineer confirms the deletion. |
| 10:35 | Cleanup job disabled. It remains disabled. |
| 13:40 | Rows restored from the 01:00 backup. Writes between 01:00 and 02:00 are lost for 6 orders. |

## What happened

The cleanup query encodes "abandoned draft" as `status = 'draft' AND updated_at < now() - 90 days`. That predicate is only correct while `'draft'` carries exactly one meaning: a customer started an order and never came back. The 11 August change gave the value a second meaning. To avoid touching many call sites, the author set the database default for `status` back to `'draft'` and had the payment code assign `pending_payment` after the row was written, so `'draft'` also came to mean "written, but not yet stamped by the payment code". The cleanup job cannot distinguish the two, and anything that sits in the unstamped state long enough looks identical to an abandoned cart. Bank transfers routinely take longer than 90 days to be given up on, so the orders most likely to sit there are exactly the ones with money in flight.

The class of defect is larger than the specific status value. A deletion predicate written as "the status nobody has changed" is default-open: it claims every row the rest of the system has not explicitly spoken for. Any state added to the order model in future silently joins the delete set unless somebody remembers this one query, and nothing in the codebase or the review process makes them remember. The job is a consumer of the status vocabulary that does not appear anywhere near the definition of that vocabulary.

## What we still do not know

The account above does not yet explain the 4,200 rows, and this gap has to be closed before anything is re-enabled.

Deleting on `updated_at < now() - 90 days` on 14 August means every deleted row had gone untouched since roughly 16 May, about twelve weeks before the change merged. A row created after 11 August cannot have been old enough to match. So either those rows already held `status = 'draft'` and something else had been keeping the job away from them until 14 August, or the 11 August change wrote `'draft'` onto existing old rows without moving `updated_at`, which a raw SQL backfill or a column rewrite applying a new default would do. The second is more likely and should be checked first by reading the migration as it actually ran against production, not as it reads in review.

Separately, we can still reconstruct what was deleted even though the job did not log it: the 01:00 backup and the post-restore table state give us the deleted set by difference. That reconstruction tells us how many live orders were affected, which customers to contact, and whether the 4,200 are all bank-transfer orders or include a second cause we have not yet identified.

## Why it was not caught earlier

The change was reviewed by one person, and review scope was the diff. Nothing prompted either party to ask which queries read the `status` column, so the cleanup job never entered the conversation. A change to a column default and to the vocabulary of a state machine is a change to every consumer of that column, and our review process treats it as a local edit.

Staging could not have surfaced this. The environment holds no orders older than 30 days, so a bug whose trigger is a 90-day age threshold is invisible there by construction. Any deletion job gated on age is untestable in an environment whose data is younger than the gate.

Detection depended entirely on a customer noticing and telephoning. Deleting 4,200 rows in four minutes produced no alert, no anomaly signal, and no log line that a human would read. Had the affected customers been less attentive, or had the deletion happened on a Friday night, the gap between deletion and discovery would have exceeded backup retention granularity and made the recovery materially worse.

## What went well

The restore path worked and was exercised under pressure for the first time in a while. Backups were an hour old rather than a day old, which held permanent data loss to 6 orders instead of thousands. The job touches a single table, so the blast radius was bounded to orders and did not require reasoning about referential damage elsewhere.

## Action items

Owners and dates are left blank; I do not have the assignments and they should be filled in at the review meeting rather than guessed here.

**Before the cleanup job is re-enabled**

1. Read the 11 August migration as executed against production and establish how rows last updated before 16 May came to hold `status = 'draft'`. Until this is answered we do not know the trigger.
2. Reconstruct the deleted set by diffing the 01:00 backup against the restored table. Publish the count of live orders affected and hand the customer list to support.
3. Contact the 6 customers whose 01:00–02:00 writes were lost, and check each for a payment confirmation that we no longer hold.
4. Rewrite the query to select on an explicit positive statement that an order is abandoned, rather than on the absence of any other status. An allowlist of statuses eligible for deletion, failing closed on any value it does not recognise, is the minimum.
5. Add a dry-run mode that emits the primary keys it would delete, and run the job in dry-run against a production replica for at least a week with the output reviewed by a person.
6. Add a volume circuit breaker: refuse to run and page if the candidate count exceeds a multiple of the trailing median.

**Follow-up**

7. Add soft delete to the orders table with a `deleted_at` column and a separate purge step that runs on a delay, so recovery is an `UPDATE` rather than a restore.
8. Log every deleted primary key and its status, with retention long enough to cover the detection gap we actually have rather than the one we would like.
9. Alert on bulk deletion from the orders table regardless of source, so that the next occurrence is detected in minutes rather than by telephone.
10. Seed staging with orders aged across the full range the production data spans, so that age-gated behaviour is reachable before it reaches customers.
11. Add to the review checklist: a change to a status vocabulary or a column default requires enumerating the queries that read that column, with the search results in the pull request.
12. Audit the codebase for other deletion or archival queries that identify their targets by the absence of an explicit status, and fix them under the same rule as item 4.