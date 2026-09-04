# Postmortem: nightly cleanup job deleted 4,200 live orders

**Date of incident:** 14 August 2026
**Status:** Resolved; cleanup job remains disabled
**Author:** Mark Maglana

## Summary

The nightly draft-order cleanup job deleted 4,200 live customer orders that were awaiting bank transfer. The job deletes rows matching `status = 'draft' AND updated_at < now() - interval '90 days'`. A change merged on 11 August introduced a `pending_payment` status but left the database default for `status` as `'draft'`, so orders awaiting payment were represented as drafts for as long as the payment code failed to overwrite that value. Bank transfers routinely take longer than 90 days to be abandoned, so a population of legitimate orders satisfied the deletion predicate exactly.

The deletion was not detected by any system. A customer telephoned support seven hours later to ask where their order had gone. All 4,200 rows were restored from the 01:00 backup by 13:40; 6 orders permanently lost changes made between 01:00 and 02:00.

## Impact

4,200 customer orders were unavailable for between 3 hours 40 minutes and 11 hours 40 minutes, depending on when each was next accessed. Six of those orders lost an hour of writes and cannot be recovered from backup. Any customer who checked their order between 02:04 and 13:40 saw it as missing rather than as pending, and at least one was told nothing useful for 70 minutes while support escalated. The financial exposure on the affected orders was not quantified during the response and should be.

## Timeline

| Time | Event |
| --- | --- |
| 11 Aug | `pending_payment` status merged. Database default for `status` set to `'draft'`; payment code updates the row to `pending_payment` after insert. Reviewed by one person; the cleanup job is not mentioned. |
| 14 Aug 02:00 | Cleanup job starts. |
| 14 Aug 02:04 | Job finishes. 4,200 rows deleted. Only the count is logged; no identifiers are recorded. |
| 14 Aug 09:20 | A customer telephones support to ask why their order has disappeared. |
| 14 Aug 09:55 | Support escalates to engineering (35 minutes). |
| 14 Aug 10:30 | Engineer confirms mass deletion (35 minutes). |
| 14 Aug 10:35 | Cleanup job disabled. |
| 14 Aug 13:40 | 4,200 rows restored from the 01:00 backup (3 hours 5 minutes). 6 orders lose writes made between 01:00 and 02:00. |

Time to detect: 7 hours 16 minutes. Time to mitigate: 8 hours 35 minutes. Time to restore: 11 hours 40 minutes.

## What caused it

The proximate cause is that `'draft'` was both the default state of a newly written row and the state a destructive job was configured to delete. Every code path that inserted an order without immediately setting a status produced a deletion candidate, and the cleanup job had no way to distinguish an order abandoned by a customer from an order sitting correctly in a payment workflow. The 90-day threshold, chosen to be conservative for genuine drafts, is shorter than the ordinary lifetime of a bank transfer, so the safety margin worked in reverse.

The decision to set the default back to `'draft'` was made to avoid touching many call sites. That is a reasonable instinct about blast radius, and it happened to be exactly the wrong tradeoff here: it reduced the number of files changed by moving risk into a column default that no reviewer of that diff would connect to a deletion query living elsewhere in the codebase.

Two conditions kept it invisible. The review covered one diff and one reviewer, and nothing in the tooling links a change to the `status` enum with the jobs that read it, so the cleanup query was never brought into the discussion. Staging holds no orders older than 30 days, so no test environment could have produced a row that satisfied a 90-day predicate. The interaction was undetectable by every mechanism the team had.

## Why detection took seven hours

Nothing watched the job. It logs a count and no identifiers, which means that even after the count was available it could not answer which rows were affected. There is no alert on deletion volume, so a jump from a normal night's handful of abandoned drafts to 4,200 rows passed silently. There is no soft delete on the table, so the rows were gone rather than marked, and confirming what had happened required reading a backup rather than querying the live table. Detection fell to a customer noticing on their own behalf, which is the slowest and most damaging detection path available.

## Open question

The row population does not reconcile with the timeline, and the investigation is not finished. Rows more than 90 days old on 14 August were last updated before roughly 16 May, which is three months before the `pending_payment` change was merged. The new write path alone cannot have produced 4,200 rows that old in three days. Something converted a pre-existing population of awaiting-payment orders into `status = 'draft'` without touching `updated_at`, and the most likely candidate is the migration itself backfilling existing rows to the new column default. Until that is confirmed against the migration and the 01:00 backup, the corrective actions below should be treated as necessary but possibly not sufficient, because a backfill that rewrites status without bumping `updated_at` is a second defect with its own reach.

## Corrective actions

1. **Stop deleting on a default value.** Change the cleanup predicate so it matches an explicit, positively-set marker for customer-abandoned drafts rather than the state a row falls into on insert. No destructive job should target a value that a row can acquire by omission.
2. **Confirm the backfill hypothesis.** Read the 11 August migration and compare `updated_at` distributions in the 01:00 backup against the current table. If the migration rewrote existing rows, audit for other columns it touched and for other jobs keyed on those columns.
3. **Add soft delete to the orders table.** Deletion becomes a status transition with a retention window, so recovery is a query rather than a restore, and the 1-hour backup granularity stops determining data loss.
4. **Give the job a dry-run mode and row-level logging.** It should log the primary keys it intends to delete, and a dry run should be the default in every environment except production.
5. **Alert on deletion volume.** Page when any batch job deletes more than a small multiple of its trailing baseline, and halt the job rather than letting it run to completion.
6. **Age the staging dataset.** Staging needs orders spanning at least 120 days, either seeded or time-shifted, so that any predicate with a 90-day threshold can actually fire there.
7. **Link status changes to their consumers.** Require that changes to the order status enum or its column default name every scheduled job that reads `status`, enforced through ownership rules on the migration directory and a checklist item in the review template.
8. **Quantify the exposure on the 4,200 orders and contact the 6 customers** whose 01:00 to 02:00 changes were lost, since those changes are gone and only the customer can restate them.

The cleanup job stays disabled until items 1, 3 and 4 are shipped.

## What went well

The restore was clean and complete within the limits of an hourly backup, and the engineer who took the escalation disabled the job before beginning recovery, which prevented a second deletion the following night. The 01:00 backup existed, was current, and restored without incident.