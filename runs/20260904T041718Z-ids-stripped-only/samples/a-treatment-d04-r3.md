# Incident postmortem: nightly cleanup job deleted 4,200 live orders

**Date of incident:** 14 August 2026
**Impact window:** 02:04 to 13:40 (11h 36m of missing orders)
**Data loss:** 6 orders lost changes made between 01:00 and 02:00; not recoverable
**Status of the job:** disabled since 10:35, still disabled

## Summary

The nightly draft-order cleanup job deleted 4,200 live customer orders that were awaiting bank transfer. The job's delete predicate had been correct for as long as `status = 'draft'` meant "an abandoned draft"; a change merged on 11 August broke that meaning by making `'draft'` the column default for rows that were not drafts. Orders awaiting a bank transfer routinely sit for more than 90 days, so they satisfied both halves of the predicate and were deleted. No alerting fired on a four-minute run that removed 4,200 rows, and nobody inside the company noticed. Detection came seven hours later from a customer telephoning support to ask where their order had gone. All 4,200 rows were restored from the 01:00 backup by 13:40, at the cost of one hour of writes on 6 of them.

## Timeline

| Time (14 August unless noted) | Event |
| --- | --- |
| 11 Aug | Change merged introducing `pending_payment`; `status` column default set to `'draft'`, payment code updates the row afterwards |
| 02:00 | Cleanup job starts |
| 02:04 | Cleanup job finishes, having deleted 4,200 rows. No alert, no per-row log |
| 09:20 | Customer telephones support asking why their order has disappeared |
| 09:55 | Support escalates to engineering |
| 10:30 | Engineer confirms the deletion and identifies the cleanup job |
| 10:35 | Cleanup job disabled |
| 13:40 | 4,200 rows restored from the 01:00 backup |

## What happened

The cleanup job deletes rows where `status = 'draft'` and `updated_at < now() - 90 days`. The 11 August change added a new status, `pending_payment`, for orders awaiting a bank transfer, but rather than update every call site that writes an order, the author kept the database default at `'draft'` and had the payment code set `pending_payment` in a second write after the row was created. From that point on, `'draft'` carried two meanings at once: a genuine abandoned draft, and a row whose real status had not yet been applied or never was. The cleanup job only understands the first meaning, and nothing in the schema or the code told it the second one now existed.

The 90-day threshold is what turned a latent modelling error into a deletion. A bank transfer is slow, and an order legitimately awaiting one can sit far past 90 days without being abandoned. Any such order carrying the default `'draft'` was therefore indistinguishable from an order the job was built to remove.

## Contributing factors

- **A default value that overlaps a meaningful value.** `'draft'` is both a real state and the placeholder for "not yet set". Any query that reads `status` inherits that ambiguity, and there were no other guards to catch it.
- **The job is unauditable.** There is no dry-run mode and no per-row logging, only a count. When the engineer arrived at 10:30 there was no record of which rows had gone; the deletion had to be reconstructed by comparing against the backup.
- **The delete is hard.** With no soft delete on the table, the only recovery path was a full restore from an hourly backup, which is what cost 6 orders an hour of writes.
- **No bound on blast radius.** A job whose normal output is a modest number of abandoned drafts deleted 4,200 rows without tripping anything. There is no sanity threshold on rows affected and no alert on bulk deletes.
- **The review had no reason to look at the job.** One reviewer, and the cleanup job was never mentioned. Nothing links a change to `status` to the queries that consume it.
- **Staging could not have caught this.** It holds no orders older than 30 days, so an interaction that only appears past 90 days is invisible there by construction.

## Detection and response

Detection was the weakest part of the incident. Seven hours and sixteen minutes passed between the deletion and the first signal, and the signal was a customer. A further thirty-five minutes went by in support before escalation, and thirty-five more before an engineer confirmed what had happened. Once engineering was involved the response was quick: the job was disabled five minutes after confirmation, and the restore completed just over three hours later.

## Open questions

These need answers before the job is re-enabled, and two of them affect our confidence in the account above.

1. Why did the 12 and 13 August runs not delete these rows? As described, the mechanism should have fired on the first nightly run after the change, not the third. Check the 11 August migration for a backfill that reset `status` while leaving `updated_at` untouched, and check whether the job ran at all on the two intervening nights.
2. How many of the 4,200 were genuinely abandoned drafts? The restore returned every deleted row, including any the job would have removed correctly. The table currently holds records that should be gone.
3. For the affected orders, did the payment code's second write fail, or never run? A race and a design gap need different fixes.
4. Were downstream consumers of order data notified of the delete and then the restore, and are they consistent with the database now?

## Action items

| Action | Addresses | Priority |
| --- | --- | --- |
| Change the `status` default to a value that means nothing else, or drop the default and make `status` NOT NULL so every writer states it | Root cause | P0 |
| Add a positive guard to the cleanup predicate: delete only rows that have never had a payment intent, rather than only rows that look like drafts | Root cause | P0 |
| Add soft delete to the orders table and convert the job to set a deleted flag, with a separate reaper for rows soft-deleted beyond the retention window | Hard delete, recovery cost | P0 |
| Abort the job and alert if the candidate set exceeds a threshold of normal volume | Blast radius, detection | P0 |
| Add a dry-run mode and log every deleted row id with its status and `updated_at` | Auditability | P1 |
| Alert on bulk deletes against customer tables regardless of source | Detection | P1 |
| Seed staging with orders aged past every retention boundary the system uses, including 90 days | Staging gap | P1 |
| Record the consumers of `status` where the enum is defined, and require them to be named in the review of any change to it | Review gap | P1 |
| Reconcile the 4,200 restored rows: purge those that were correctly abandoned, and repair the 6 orders that lost writes | Restore side effects | P1 |
| Decide the re-enable criteria for the job and the interim plan for abandoned drafts, which are now accumulating | Accepted risk | P2 |