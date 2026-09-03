# Incident Postmortem: Nightly cleanup job deleted 4,200 live orders

**Date of incident:** 14 August
**Status:** Mitigated (data restored; cleanup job disabled and remains disabled)
**Severity:** High — customer-visible loss of live records, with a small amount of permanent data loss

---

## Summary

The nightly draft-order cleanup job deleted 4,200 live customer orders that were awaiting bank transfer payment. The job deletes rows where `status = 'draft'` and `updated_at` is older than 90 days. A change merged on 11 August introduced a new status, `pending_payment`, but wrote it as a second step after the row was created with the database default of `'draft'`. Orders awaiting bank transfer routinely sit for more than 90 days, so awaiting-payment orders that were still carrying `'draft'` matched the cleanup query and were hard-deleted.

The deletion was not detected by monitoring. A customer telephoned support seven hours later to ask where their order had gone. Rows were restored from the 01:00 backup, which cost an hour of changes on 6 orders.

## Impact

- **4,200 orders** deleted at 02:00–02:04 and unavailable to customers and staff until 13:40 — approximately **11 hours 36 minutes**.
- **6 orders** permanently lost changes made between 01:00 and 02:00, because the restore came from the 01:00 backup. These need individual reconciliation with the customers concerned.
- Unknown volume of downstream effects: support contacts, abandoned checkouts, and any external systems that read or reconciled against these orders during the outage window. Not yet quantified.
- The cleanup job has been disabled since 10:35, so abandoned drafts are accumulating.

## Timeline (all times 14 August unless noted)

| Time | Event |
|---|---|
| 11 Aug | Change introducing `pending_payment` merged, reviewed by one person |
| 02:00 | Cleanup job starts |
| 02:04 | Job finishes; 4,200 rows deleted; only a count is logged |
| 09:20 | Customer telephones support asking why their order has disappeared |
| 09:55 | Support escalates (35 min) |
| 10:30 | Engineer confirms the deletion (35 min) |
| 10:35 | Cleanup job disabled |
| 13:40 | Rows restored from the 01:00 backup |

**Time to detect:** 7h 16m from the deletion, and detection came from a customer, not from us.
**Time to mitigate (job disabled):** 8h 31m.
**Time to restore:** 11h 36m.

## What happened

The `status` column carried two distinct meanings after 11 August. For the cleanup job, `'draft'` meant "an abandoned shopping basket, safe to delete once stale." For the new payment flow, `'draft'` was also the transient value every row holds between being inserted and being stamped `pending_payment` by the payment code. Nothing in the schema or the code distinguished the two.

Splitting the write into two steps means there is a population of rows for which the second step never lands — a failed request, a crashed worker, an order created through a path that does not run the payment code. Those rows keep `'draft'` permanently, and because nothing further touches them, `updated_at` stops advancing. After 90 days they are indistinguishable, to the cleanup query, from an abandoned basket.

The 90-day threshold itself encodes an assumption that no longer holds. It is a plausible definition of "abandoned" for a shopping basket and a wrong one for a bank transfer, which commonly takes longer than 90 days to be genuinely abandoned. Even with the status filter corrected, we do not currently have an agreed retention rule for the awaiting-payment flow.

### One link is not yet established

The change merged on 11 August and the job ran on 14 August. Rows created after the merge could not have aged past 90 days in three days, so the 4,200 deleted rows were created *before* the merge and were holding `status = 'draft'` at 02:00 on 14 August. The mechanism above explains how *newly created* awaiting-payment orders can be left as `'draft'`; it does not explain how *pre-existing* ones came to hold that value.

Two candidate explanations, with different remediations:

1. **The 11 August change also moved existing rows.** A backfill, or a table rewrite triggered by the migration, set existing awaiting-payment orders to the new default `'draft'`. The payment code only stamps `pending_payment` at creation time, so those rows were never corrected.
2. **Those rows already held `'draft'` and something else changed.** If so, the 11 August change is not the trigger and the true cause is elsewhere — for example the job not having run, or having run with different parameters, for the preceding 90 days.

This should be settled before any fix is designed. Concretely: read the 11 August migration; compare `created_at`/`updated_at` on the restored rows against the merge date; and pull the cleanup job's run history and per-run deletion counts for the last several months. **This is action item 1.**

## Contributing factors

- **An overloaded status value.** `'draft'` meant both "abandoned" and "not yet stamped," with no way for a reader to tell them apart.
- **A default-then-update write.** Setting the status in the same statement that inserts the row would have removed the ambiguous intermediate state entirely.
- **No coupling between the status vocabulary and the destructive job.** Adding a status value could not fail any test or check that knows the cleanup job exists.
- **The job has no safety features.** No dry-run, no row-level logging (only a count), no soft delete on the table, and no guardrail that aborts when the deletion set is implausibly large. 4,200 rows in one night produced no signal of any kind.
- **Review did not reach the blast radius.** One reviewer, and the cleanup job was not raised. There is no mechanism that would have surfaced it — finding it required already knowing it existed.
- **Staging cannot reproduce age-dependent behaviour.** It holds no orders older than 30 days, so no amount of testing there would have exposed a 90-day condition.
- **Detection depended on a customer noticing.** There is no alerting on deletion volume or on order-count drops.

## What went well

- A recent backup existed and the restore worked, holding data loss to one hour on 6 orders.
- Once support escalated, confirmation took 35 minutes and the job was disabled 5 minutes after that.
- The job was left disabled rather than re-enabled under time pressure.

## Action items

| # | Action | Priority |
|---|---|---|
| 1 | Establish how pre-existing awaiting-payment rows came to hold `'draft'` (see above). Confirm the cause before building the fix. | P0 |
| 2 | Verify the restore was complete — reconcile restored row count against the deleted count, not just "the restore ran." | P0 |
| 3 | Contact the 6 customers whose 01:00–02:00 changes were lost and reconstruct those changes where possible. | P0 |
| 4 | Keep the cleanup job disabled until items 5–8 ship. Agree an interim plan for the drafts now accumulating. | P0 |
| 5 | Add soft delete (`deleted_at`) to the orders table. The cleanup job sets it; a separate, later, independently reviewed purge does the hard delete. | P1 |
| 6 | Add a blast-radius guardrail: the job aborts and pages if the candidate set exceeds an absolute threshold or a percentage of the table. | P1 |
| 7 | Add a dry-run mode and per-row logging of order IDs, so a bad run is reconstructible without a restore. | P1 |
| 8 | Rewrite the cleanup query as an explicit allowlist of statuses that are safe to delete, with a test that enumerates every status value and asserts its disposition. New statuses then fail closed. | P1 |
| 9 | Fix the write path so `status` is set in the insert rather than defaulted and updated. Audit current `'draft'` rows for any that are actually awaiting payment. | P1 |
| 10 | Alert on daily deleted-row counts and on order-count drops, so the next occurrence is detected in minutes rather than by a phone call. | P1 |
| 11 | Agree an explicit retention rule for the awaiting-payment flow. 90 days is the wrong number for bank transfer. | P2 |
| 12 | Give staging time-shifted fixtures so age-dependent jobs can be exercised there. | P2 |
| 13 | Require changes to shared status vocabularies to identify consumers; add ownership on the cleanup job so its owners are pulled into such reviews. | P2 |

Owners and dates are not assigned in this draft and need to be filled in before this is signed off.