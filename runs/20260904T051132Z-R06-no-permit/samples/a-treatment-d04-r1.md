# Postmortem: nightly cleanup job deleted 4,200 live orders

**Date of incident:** 14 August 2026
**Severity:** high (customer-visible data loss, partially unrecoverable)
**Status:** mitigated; cleanup job disabled pending remediation

## Summary

The nightly draft-order cleanup job deleted 4,200 live customer orders between 02:00 and 02:04 on 14 August. The job deletes rows where `status = 'draft'` and `updated_at` is older than 90 days. A change merged on 11 August introduced a new status, `pending_payment`, for orders awaiting a bank transfer, and left `'draft'` as the database default so that the payment code could set the new value in a second write after the row was created. Orders awaiting a bank transfer routinely sit for longer than 90 days, and the ones that were carrying `status = 'draft'` with an old `updated_at` matched the cleanup predicate exactly. The job deleted them.

Nothing in the system noticed. The job's only output is a count, the table has no soft delete, and no alert fires on deletion volume. Detection came from a customer who telephoned support at 09:20 to ask where their order had gone, seven hours and sixteen minutes after the deletion completed. All 4,200 rows were restored from the 01:00 backup by 13:40. Six orders had been modified between 01:00 and 02:00; those changes are permanently lost.

## Impact

| Measure | Value |
| --- | --- |
| Rows deleted | 4,200 live customer orders |
| Data unavailable | 02:04 to 13:40 (11 h 36 m) |
| Permanent data loss | 6 orders, changes made 01:00 to 02:00 |
| Time to detect | 7 h 16 m (customer report) |
| Time to confirm | 8 h 26 m |
| Time to mitigate | 8 h 31 m (job disabled) |
| Time to restore | 11 h 36 m |
| Customer reports received | 1 |

The single customer report is not a measure of customer impact. It is a measure of how many affected customers happened to look at their order during business hours on the day it vanished. Every one of the 4,200 was exposed for the full window.

## Timeline

All times are on 14 August unless stated.

| Time | Event |
| --- | --- |
| 11 Aug | Change introducing `pending_payment` merged. Database default for `status` set to `'draft'`; payment code sets `pending_payment` in a subsequent write. Reviewed by one person. The cleanup job is not mentioned in the review. |
| 01:00 | Nightly backup taken. This becomes the restore point. |
| 02:00 | Cleanup job starts. |
| 02:04 | Cleanup job finishes, having deleted 4,200 rows. It logs a count and nothing else. No alert fires. |
| 09:20 | A customer telephones support to report a missing order. |
| 09:55 | Support escalates to engineering. |
| 10:30 | An engineer confirms the deletion and identifies the cleanup job as the cause. |
| 10:35 | Cleanup job disabled. It remains disabled. |
| 13:40 | All 4,200 rows restored from the 01:00 backup. Six orders lose the changes made between 01:00 and 02:00. |

## What happened

The cleanup query is a definition dressed as a filter. `status = 'draft' AND updated_at < now() - 90 days` is the system's operative definition of "an abandoned draft order", and it lives in the cleanup job, far from the code that assigns statuses and with nothing connecting the two. Any change to the meaning of `'draft'` is silently a change to what the job deletes, and the author of such a change gets no signal that they have made one.

The 11 August change made exactly that change to the meaning of `'draft'`. The stated reason for leaving the default as `'draft'` and applying `pending_payment` in a second write was to avoid touching many call sites, which is a reasonable thing to want. The cost of that choice was that `'draft'` stopped meaning "the customer has not submitted this order" and started also meaning "this row has not yet been classified". The cleanup job only understands the first meaning, and it acts on the difference by issuing a hard `DELETE`.

The 4,200 deleted rows carried `status = 'draft'` with an `updated_at` older than 90 days. How they came to carry `'draft'` is not established by what we know so far, and it matters, because the correct fix differs depending on the answer. If the second write that sets `pending_payment` had run and persisted for every bank-transfer order, those rows would not have matched the predicate. Two explanations are consistent with the evidence. Either the second write is not universal, so that some path creates a bank-transfer order and never reclassifies it, or the change altered the status of long-lived orders that already existed, through the new default or a backfill, without touching their `updated_at`. The first is an ongoing bug that will keep producing vulnerable rows. The second is a one-off population that has now been restored. The restored rows are currently the only record of what was deleted, since the job logs no identifiers, and they can settle this question directly. Doing so is the first action item below.

Three properties of the cleanup job turned a wrong query into an incident rather than a caught mistake. It has no dry-run mode, so the predicate change could not have been evaluated against production data without deleting. It logs only a count, so a night that destroyed 4,200 live orders produced the same shape of output as a night that removed genuine rubbish, and nobody reading the log could tell the difference. The table has no soft delete, so the job's action was irreversible at the moment it ran and recovery depended entirely on a backup taken an hour earlier. The one-hour backup interval sets a floor on data loss for this class of incident: the best available outcome was always going to be the loss of up to an hour of writes, and we paid six orders for it.

Detection is the largest single gap. The system had no opinion about deleting 4,200 rows. A job that normally removes a small number of stale drafts removed a number several orders of magnitude larger, and there is no threshold, no comparison against the historical median, and no alert on order-count movement to catch it. Detection therefore fell to a customer, and the clock ran from 02:04 until somebody happened to look. Once the report arrived, the response was reasonable but not fast: thirty-five minutes from the customer call to escalation, and another thirty-five to confirmation.

Staging could not have caught this and cannot catch the next one. It holds no orders older than 30 days, so a predicate keyed to 90 days matches nothing there under any circumstances. Any bug in this job that depends on the age window is invisible to staging by construction.

The review of the 11 August change involved one person and did not consider readers of the `status` column. This is not a failure of attention by the reviewer. Nothing in the change indicated that a nightly job elsewhere in the system depended on the value being changed, and finding it would have required someone to think to search for consumers of `status` on their own initiative.

## What went well

The 01:00 backup existed, was current, and restored cleanly, which is why this is a recoverable incident rather than the permanent loss of 4,200 orders. The engineer who picked up the escalation identified the cause within thirty-five minutes and disabled the job five minutes after confirming it, before restoration began, which prevented a second deletion on the night of the 15th.

## Action items

Owners are unassigned; these need to be allocated before this document is closed.

| # | Action | Type | Priority |
| --- | --- | --- | --- |
| 1 | Characterise the 4,200 restored rows to determine why they held `status = 'draft'`, and confirm whether the reclassification write is still failing to persist for new orders | Investigation | P0 |
| 2 | Contact the 6 customers whose 01:00 to 02:00 changes were lost; reconstruct the changes from application logs where possible | Customer impact | P0 |
| 3 | Add a volume guardrail to the cleanup job: abort and alert if the candidate set exceeds a fixed ceiling or a multiple of the trailing median | Prevention | P0 |
| 4 | Log the primary key, status and `updated_at` of every row the job deletes, retained for at least 90 days | Detection | P0 |
| 5 | Add soft delete to the orders table: set `deleted_at`, with a separate reaper that hard-deletes after a retention window | Prevention | P1 |
| 6 | Replace the literal `status = 'draft'` with an explicit list of deletable statuses defined alongside the status enum, with a test that fails when a new status is added and not classified | Prevention | P1 |
| 7 | Drop the `'draft'` default on `status` and require the value at insert, accepting the call-site work the 11 August change avoided | Prevention | P1 |
| 8 | Add a dry-run mode and require a dry-run diff against production data on any change to the cleanup predicate | Prevention | P1 |
| 9 | Alert on order-count drops and on deletion volume from any batch job, routed to page rather than to a dashboard | Detection | P1 |
| 10 | Seed staging with orders spanning the full age range the predicate can match, or make the retention window configurable per environment | Testing | P2 |
| 11 | Give support an explicit severity trigger for "customer data is missing" that escalates without waiting for a second report | Response | P2 |
| 12 | Require changes to shared status or enum columns to enumerate the column's consumers in the review description | Process | P2 |

Items 3 and 4 are the cheapest and should land before the job is re-enabled. The job should stay disabled until items 3, 4, 6 and 8 are complete, and item 1 has answered the question of whether new vulnerable rows are still being created.