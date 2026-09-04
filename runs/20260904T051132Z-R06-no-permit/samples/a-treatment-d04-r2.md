# Postmortem: nightly cleanup job deleted 4,200 live orders

**Date of incident:** 14 August 2026
**Duration of customer impact:** 02:04 to 13:40 (11h 36m)
**Status:** Resolved; cleanup job remains disabled
**Author:** Mark Maglana
**Severity:** Customer data loss, recovered from backup with a partial gap

## Summary

The nightly cleanup job deleted 4,200 live customer orders because a change merged three days earlier made orders awaiting bank transfer indistinguishable, at the database level, from abandoned drafts. All 4,200 rows were restored from the 01:00 backup by 13:40. Six of them lost changes made between 01:00 and 02:00 and still need manual reconciliation.

The deletion is the visible failure, but it is not the interesting one. The `pending_payment` change was a reasonable piece of work that happened to collide with a query nobody involved was thinking about, and the system offered no place where that collision could surface: not in review, not in staging, not in the job's own output, and not in monitoring. We found out because a customer telephoned us seven hours later. Every safeguard that would have caught this was either absent or unable to represent the condition.

## Impact

4,200 live orders were deleted from the orders table. These were orders awaiting payment by bank transfer, which is to say orders belonging to customers who had committed to buy and were mid-transaction. For 11 hours and 36 minutes those orders did not exist as far as the customer or the application was concerned.

All 4,200 rows were restored. Because the restore came from the 01:00 backup and the deletion ran at 02:00, any write in that hour was lost; this affected 6 orders. Those 6 need to be identified to the customers or the operations team and reconstructed by hand, and that work is not yet done.

We know one customer noticed, because they called. We do not know how many others saw a missing order and did not call, and we have no way to find out retrospectively.

## Timeline

All times on 14 August unless stated.

| Time | Event |
|---|---|
| 11 Aug | Change introducing `pending_payment` merged, reviewed by one person |
| 02:00 | Nightly cleanup job starts |
| 02:04 | Job finishes, having deleted 4,200 live orders |
| 09:20 | Customer telephones support to ask why their order has disappeared |
| 09:55 | Support escalates to engineering (35m after first report) |
| 10:30 | Engineer confirms the deletion (35m after escalation) |
| 10:35 | Cleanup job disabled |
| 13:40 | 4,200 rows restored from the 01:00 backup (3h 10m after confirmation) |

Two gaps are worth naming. Nothing internal noticed for 7 hours and 16 minutes; the clock only started when a customer chose to pick up the phone. And 70 minutes elapsed between that call and an engineer confirming what had happened, which is time spent establishing that a customer's report of a missing order was a systemic event rather than a one-off support question.

## Why it happened

The cleanup job selects rows where `status = 'draft' AND updated_at < now() - 90 days`. The `pending_payment` change kept `'draft'` as the database default for `status` and had the payment code write `pending_payment` afterwards, as a second step, to avoid touching many call sites. The consequence is that "this order is awaiting a bank transfer" was not a state the row was created in; it was a state applied to the row later. Any awaiting-payment order for which that second write did not apply sat in the table as an ordinary draft, and since bank transfers commonly run past 90 days without the order being touched, those rows crossed the `updated_at` threshold and matched the query exactly as intended.

Several conditions had to hold at once for this to reach production and stay unnoticed.

**The cleanup query filters on a value, not on a meaning.** `status = 'draft'` was a correct expression of "abandoned draft" only for as long as `'draft'` had one meaning. Nothing in the schema, the code, or the review process ties the set of status values to the queries that consume them, so widening the set of things that can be `'draft'` silently widened the delete.

**The default value carried the collision.** Setting the default back to `'draft'` is what made the new state occupy the old state's name. The choice was made to avoid touching many call sites, which is a real cost and a reasonable thing to weigh; the failure was that the tradeoff was never stated as one, so nobody weighed it against the deletion path.

**Review had no way to see it.** One reviewer, and the cleanup job was not mentioned. This is not a reviewer failure. Finding this defect required knowing that a query in an unrelated nightly job depended on the semantics of the value being changed, and nothing in the diff would tell a reader that.

**Staging could not reproduce it.** Staging holds no orders older than 30 days, so a condition predicated on 90 days of inactivity cannot fire there. Any test of the cleanup job in staging passes by construction, which is worse than having no test, because it reads as coverage.

**The job could not be inspected.** No dry-run mode, so there is no way to ask what it would delete without deleting it. No per-row logging, so after the fact we have a count and nothing else. The count itself was presumably far outside the normal range and would have been a strong signal, but nothing watched it.

**Deletion was final.** No soft delete on this table, so the only recovery path was a backup restore. That path took 3 hours 10 minutes and guaranteed the loss of an hour of writes. A soft delete would have made recovery a single update and would have cost no data at all.

## What went well

The restore worked, and it worked within a few hours of confirmation. Support escalated rather than treating a missing order as a one-off, which is the judgement call that turned a support ticket into an incident. Disabling the job five minutes after confirmation was the right first move and prevented a second night of deletions.

## Open questions

These need answers before the action items can be finalised, and one of them may change the analysis above.

How many of the 4,200 were genuinely `status = 'draft'`, and why did the second write not apply to them? The account we have says awaiting-payment rows matched a query that requires `status = 'draft'`, which means the payment code's follow-up write did not take effect on those rows. Whether that is because certain creation paths never reach the payment code, because a failure mode leaves the row in its default state, or because of something else entirely, determines whether the fix is "stop using `'draft'` as the default" or something larger. Confirm this against the actual rows before writing the fix.

How were the affected rows identified for the restore? Since the job logs only a count, identification must have come from diffing the backup against the live table. That worked here. It works only while the backup is recent and the table is small enough to diff, and it is not a recovery procedure anyone designed.

Did the delete cascade to related rows, and were those restored too? Payments, audit entries, and line items associated with the deleted orders should be checked.

What is the retention policy for `pending_payment` orders? Bank transfers commonly exceed 90 days. Even with the status collision fixed, someone has to decide when an unpaid bank-transfer order is abandoned, and 90 days is evidently not the answer.

## Action items

Owners are unassigned; assign before closing this document.

1. **Reconstruct the 6 orders that lost writes between 01:00 and 02:00.** Identify them, notify the affected customers, and restore the lost changes by hand. This is the only outstanding customer-facing harm. Owner: TBD. Due: immediately.

2. **Add a soft delete to the orders table and convert the cleanup job to use it.** Hard deletion of customer records by an unattended job is the single change that turns every future mistake of this class from an eleven-hour recovery into an update statement. Owner: TBD. Priority: highest of the preventive items.

3. **Give the cleanup job a dry-run mode and per-row logging.** It should be able to report exactly which rows it would delete without deleting them, and it should log identifiers for every row it does delete. Owner: TBD.

4. **Alert on the job's delete count.** Anything outside the established normal range should page rather than proceed. A run deleting 4,200 rows would have been caught within minutes. Owner: TBD.

5. **Fix the status representation so that awaiting-payment orders are never stored as `'draft'`.** The specific fix depends on the first open question above. Whatever the mechanism, the invariant to establish is that no row is ever persisted in a state that misrepresents it, even transiently. Owner: TBD.

6. **Decide and document the retention rule for `pending_payment` orders,** and make the cleanup query an explicit allowlist of statuses rather than a filter on one value, so that a future status is out of scope by default rather than in scope by default. Owner: TBD.

7. **Give staging data that spans the ranges our jobs query.** At minimum, orders old enough for the 90-day condition to fire. Until then, no scheduled job that filters on age can be meaningfully exercised before production. Owner: TBD.

8. **Add a review trigger for changes to status enums and column defaults** that requires the author to enumerate the queries consuming that column. The reviewer could not have found this; the tooling should make the dependency visible rather than relying on someone happening to know. Owner: TBD.

9. **Plan the re-enabling of the cleanup job.** It has been disabled since 10:35 on 14 August, so genuinely abandoned drafts have been accumulating. The first run after re-enabling will have a backlog far larger than a normal night's, and it should be run in dry-run mode and inspected before it is allowed to delete anything.