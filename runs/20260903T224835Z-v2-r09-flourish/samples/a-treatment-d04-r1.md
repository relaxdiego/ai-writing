# Postmortem: nightly cleanup job deleted 4,200 live orders

**Date of incident:** 14 August · **Status:** resolved, cleanup job remains disabled · **Severity:** high (customer-visible data loss, partially permanent)

## Summary

The nightly draft-order cleanup job deleted 4,200 live customer orders between 02:00 and 02:04. The job's deletion predicate treats `status = 'draft'` as a proxy for "abandoned", and a change merged on 11 August put orders that were legitimately awaiting a bank transfer into that status. All 4,200 rows were restored from the 01:00 backup by 13:40. Six of them lost the writes made between 01:00 and 02:00, and that loss is permanent. Nothing detected the deletion: a customer telephoned support seven hours and sixteen minutes after the job finished.

## Impact

4,200 orders were absent from the product for up to eleven hours and thirty-six minutes, so customers who looked during that window saw an order they had placed simply gone. Six orders were restored to their 01:00 state and lost an hour of subsequent changes; those six need to be identified from application and payment logs and reconstructed, and the affected customers contacted. The count of customers who noticed is unknown, because we have no record of who viewed an order during the outage window. One is confirmed, being the person who called.

## Timeline

All times 14 August, as reported.

| Time | Event |
|---|---|
| 01:00 | Nightly backup snapshot taken (later the restore source) |
| 02:00 | Cleanup job starts |
| 02:04 | Job finishes. 4,200 rows deleted. Only the count is logged |
| 09:20 | Customer telephones support asking why their order has disappeared |
| 09:55 | Support escalates to engineering (35 min) |
| 10:30 | Engineer confirms the deletion and its cause (35 min) |
| 10:35 | Cleanup job disabled |
| 13:40 | All 4,200 rows restored from the 01:00 backup (3 h 10 min) |

## What happened

The cleanup job deletes rows matching `status = 'draft' AND updated_at < now() - 90 days`. That predicate encodes a business rule, "a draft nobody has touched in 90 days is abandoned", as a test against a single status string. The rule held only for as long as `'draft'` meant exactly one thing.

On 11 August a change introduced `pending_payment` for orders awaiting a bank transfer. Rather than update the many call sites that write orders, the author set the database default for `status` back to `'draft'` and had the payment code set `pending_payment` in a separate write after the row had been created. Bank transfers routinely take longer than 90 days to be given up on, so an order sitting in that flow past the 90-day mark is a live order by design, not an abandoned one. Orders in that condition carrying `status = 'draft'` matched the cleanup predicate exactly, and the job deleted them.

One fact is not settled by the information gathered so far, and the choice of remediation depends on it a little: how 4,200 rows came to hold `status = 'draft'` with an `updated_at` older than 90 days, when the change landed only three days before the deletion. Rows written after 11 August cannot satisfy the age condition. The candidate paths are:

- A data migration accompanying the default change rewrote existing awaiting-payment rows to `'draft'` without bumping `updated_at`, making 4,200 old rows newly eligible in a single step.
- Awaiting-payment orders were already being stored as `'draft'` before 11 August, and something else changed on or around that date to bring them within the job's reach.
- The post-insert write of `pending_payment` is not atomic with the insert, so rows whose second write failed remain `'draft'` indefinitely. This does not explain the 14 August deletions on its own, but it is a live defect on the same code path.

The deleted rows' pre-deletion state is recoverable from the 01:00 backup, and the 11 August migration is in version control, so this is answerable rather than merely arguable. It should be resolved before the cleanup job is re-enabled.

## Contributing factors

The change was reviewed by one person, and the cleanup job was never raised in the review. Nothing in our process connects a change to the vocabulary of `status` with the set of queries that read `status`, so the reviewer had no prompt to go looking. Staging could not have caught it either: it holds no orders older than 30 days, which means any bug whose trigger is an age threshold of 90 days is structurally invisible there, not merely unlikely to appear.

Once the job ran, every property of the job worked against us. It has no dry-run mode, so its effect could not be inspected before it took it. It logs a count and nothing else, so at 10:30 the engineer could tell that 4,200 rows had gone but not which ones, and the identification of the 4,200 came from the backup rather than from us. There is no soft delete on the table, so the deletion was immediate and total, and recovery required a restore rather than an update. No alert fires on deletion volume, so a run deleting 4,200 rows was indistinguishable to our monitoring from a run deleting none.

## What went well

After confirmation at 10:30 the response was quick and clean. The job was disabled five minutes later, the 01:00 backup was present and usable, and the full restore completed in three hours and ten minutes with 4,199 of 4,200 rows recovered intact in substance and only six carrying any loss at all.

## Action items

| # | Action | Kind |
|---|---|---|
| 1 | Determine which mechanism produced 4,200 `'draft'` rows older than 90 days, using the 01:00 backup and the 11 August migration. Blocks re-enabling the job | Investigate |
| 2 | Identify the 6 orders with lost writes, reconstruct from payment and application logs, contact those customers | Remediate |
| 3 | Replace the cleanup predicate with an explicit allowlist of terminal statuses it may delete, failing closed on any status value it does not recognise | Prevent |
| 4 | Add soft delete (`deleted_at`) to the orders table; the cleanup job sets it, and a separate purge hard-deletes after a retention window | Mitigate |
| 5 | Log the primary key and status of every row the job deletes, written before the delete | Detect |
| 6 | Add a dry-run mode, and an abort threshold: the job stops and alerts rather than deleting when the candidate count exceeds its trailing norm | Prevent |
| 7 | Make the payment path write `pending_payment` atomically with the insert, or reconcile rows stuck in `'draft'` on that path | Prevent |
| 8 | Require a consumer audit for any change to the `status` vocabulary: every query filtering on `status` listed in the pull request, reviewed by an owner of the batch jobs | Prevent |
| 9 | Seed staging with age-representative data spanning past the longest threshold used by any job, currently 90 days | Prevent |
| 10 | Alert on per-job deletion volume | Detect |
| 11 | Decide the correct handling of bank transfers still open past 90 days, since the rule "90 days idle means abandoned" is false for that flow | Prevent |

Owners and target dates are not assigned in this document and need to be set before it is closed.

## Lesson

A batch job that deletes rows is a consumer of every column it filters on, and the `status` column had an implicit contract that nobody had written down: that `'draft'` means abandoned-in-progress and nothing else. The 11 August change was reasonable in isolation and broke that contract without anyone in the review being in a position to notice, because we have no mechanism that surfaces the consumers of a status value to the person changing it. The predicate should have been an allowlist from the start, so that a status value the job had never seen was a reason to stop rather than a row to delete.