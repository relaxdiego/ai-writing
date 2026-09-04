# Postmortem: nightly cleanup job deleted 4,200 live orders

**Incident date:** 14 August · **Severity:** high · **Status:** resolved; cleanup job disabled and remaining disabled

## Summary

The nightly draft-cleanup job deleted 4,200 live customer orders that were awaiting bank transfer, and the deletion was found by a customer rather than by us.

The job's selection query treats `status = 'draft'` plus 90 days without an update as sufficient evidence that an order has been abandoned. A change merged on 11 August introduced a new status, `pending_payment`, for orders awaiting a bank transfer, but left the database default for `status` as `'draft'` and set the new value from the payment code in a second write. Orders awaiting payment that were still carrying `'draft'` therefore fell inside the cleanup job's definition of abandoned, and bank transfers routinely sit open for longer than 90 days. The rows were restored from the 01:00 backup, at the cost of one hour of writes on 6 of them.

## Impact

Four thousand two hundred live orders were absent from the system for between 9 and 11.5 hours, depending on when a given customer looked. Six of those orders lost every change made between the 01:00 backup and the 02:00 deletion; that data is not recoverable and those customers need to be contacted and their orders reconciled by hand. One customer reported the problem. We have no way to count how many others saw a missing order and did not call, and no way to count orders that were not merely missing but were acted on downstream while absent.

Because the job logs only a count and the table has no soft delete, the engineer who confirmed the incident at 10:30 could not enumerate what had been removed. Recovery had to restore the whole affected population rather than a targeted set, which means any orders in the 4,200 that the job was legitimately entitled to delete have been resurrected and will be deleted again once the job is safe to run.

## Timeline (14 August, all times local)

| Time | Event | Elapsed |
|---|---|---|
| 01:00 | Nightly backup taken | |
| 02:00 | Cleanup job starts | |
| 02:04 | Job finishes; 4,200 rows deleted, count logged, no row identifiers recorded | |
| 09:20 | Customer telephones support asking why their order has disappeared | 7h 16m after deletion |
| 09:55 | Support escalates to engineering | +35m |
| 10:30 | Engineer confirms the rows were deleted by the cleanup job | +35m |
| 10:35 | Cleanup job disabled | +5m |
| 13:40 | Rows restored from the 01:00 backup | +3h 10m |

The 11 August merge that introduced `pending_payment` sits three days before the job run and is the origin of the fault.

## Root cause

The cleanup job and the status change disagreed about what `'draft'` means, and nothing in the system forced that disagreement into the open. To the cleanup job, `'draft'` was a terminal state that only decays into abandonment. To the 11 August change, `'draft'` became a transient value that a row holds until the payment code overwrites it, chosen specifically so that existing call sites would not have to be touched. Leaving the default as `'draft'` is what made the change cheap to write, and it is also what put a live business state inside the deletion job's blast radius.

The deeper problem is that the meaning of the row depended on a second write succeeding. A row that is genuinely awaiting a bank transfer is indistinguishable, in the database, from a row that was created and forgotten, unless the follow-up update ran. Any deletion policy built on `status` alone inherits that ambiguity.

## Contributing factors

- **The query deletes by inclusion in a value that anyone can reuse.** Every new meaning attached to `'draft'` silently enters the job's scope, with no code change to the job and nothing to review.
- **Review did not reach the consumers of the column.** One reviewer approved the change; the cleanup job was never raised. Nothing links a change in a status vocabulary to the code that reads that column.
- **Staging could not have shown this.** It holds no orders older than 30 days, so a bug whose trigger is a 90-day threshold is invisible there by construction.
- **The job has no dry-run mode and no per-row logging.** Its first observable effect is an irreversible one, and its output is a number.
- **The table has no soft delete.** Recovery required a backup restore rather than an update.
- **Nothing alerted on deletion volume.** A run that removed 4,200 rows produced the same kind of log line as a run that removes a handful, and no one was watching either.
- **Detection depended on a customer.** Seven and a quarter hours passed before the first report, and another 70 minutes passed inside support and escalation before an engineer looked.

## What we do not yet know

We have not established why these specific 4,200 rows still carried `'draft'` with an `updated_at` older than 90 days. The payment code's second write should have set `pending_payment` and refreshed `updated_at`, which would have excluded them on both halves of the predicate. Until we can explain that, we do not know the true size of the at-risk population, and re-enabling the job would be guessing. This is the blocking item.

## Action items

1. **Keep the job disabled** until items 2, 3 and 4 are in place and the open question above is answered.
2. **Set the status at write time.** Remove the `'draft'` default, or make the column require an explicit value, so that no row's meaning rests on a follow-up update. Touching the call sites is the work that was avoided on 11 August and it is the correct fix.
3. **Rewrite the selection positively.** Delete only rows whose status appears in an explicit, reviewed list of states that are safe to purge, and add a guard excluding any row with an associated payment intent or bank transfer, so that a future status value defaults to being kept rather than deleted.
4. **Add a volume guard.** The job aborts and alerts if a run would delete more than a configured absolute count or more than a set multiple of the trailing median, rather than proceeding.
5. **Add soft delete to the orders table**, with a separate purge after a retention window, so that a mistake of this kind is an update to reverse rather than a restore to schedule.
6. **Add a dry-run mode and per-row logging.** Retain the identifiers of everything deleted for at least the retention window; the count alone cost us three hours of blind recovery.
7. **Give staging aged data**, or run destructive jobs in dry-run against a restored production snapshot before they run for real. A 90-day rule cannot be tested against a 30-day dataset.
8. **Require consumer identification for status-vocabulary changes.** A change that adds or repurposes a value in `status` must list the readers of that column in the review, cleanup and reporting jobs included, and needs a second reviewer.
9. **Contact the 6 customers** whose orders lost an hour of changes and reconcile those orders manually.
10. **Shorten the detection path.** Support needs a documented route for "data has disappeared" that escalates immediately, and engineering needs an alert that fires on the deletion volume rather than on a phone call.

The one-hour gap between backup and job run cost 6 orders their most recent changes. Point-in-time recovery would have reduced that to near zero and is worth costing out, though it ranks below the items that stop the deletion happening at all.