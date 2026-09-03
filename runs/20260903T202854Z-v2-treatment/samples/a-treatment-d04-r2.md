# Incident postmortem: nightly cleanup job deleted 4,200 live orders

**Date of incident:** 14 August 2026
**Severity:** High — bulk loss of live customer data, with a partial permanent component
**Status:** Mitigated; cleanup job remains disabled pending remediation
**Owners and target dates below are unassigned and need to be filled in before this document is closed.**

## Summary

A nightly cleanup job intended to remove abandoned draft orders deleted 4,200 live customer orders that were awaiting bank transfer. The job's query used `status = 'draft'` as a proxy for "abandoned", and a change merged on 11 August made `'draft'` the resting value for a second, entirely different lifecycle. Orders awaiting payment for more than 90 days, which is normal for bank transfers, matched the query exactly. Nothing in the system noticed. Detection came from a customer telephoning support seven hours and twenty minutes after the deletion.

## Impact

4,200 live orders were deleted at 02:00 and were absent from the product until the restore completed at 13:40, a customer-visible outage of that data lasting 11 hours 40 minutes. All 4,200 rows were recovered from the 01:00 backup. Because the backup predates the deletion by an hour, any modification made to these orders between 01:00 and 02:00 was lost permanently; this affected 6 orders. Those 6 customers need to be contacted individually, and we do not currently know what the lost changes were, because the job logs only a count and there is no write-ahead record of the affected rows.

An unknown number of customers encountered a missing order and did not call. One did call, and that is the only reason we know about any of this.

## Timeline

All times 14 August, local.

| Time | Event |
|---|---|
| 02:00 | Cleanup job starts. |
| 02:04 | Job finishes, having deleted 4,200 live orders. No alert fires. |
| 09:20 | A customer telephones support to ask why their order has disappeared. |
| 09:55 | Support escalates to engineering (35 minutes after first contact). |
| 10:30 | An engineer confirms bulk deletion (35 minutes after escalation). |
| 10:35 | Cleanup job disabled. |
| 13:40 | 4,200 rows restored from the 01:00 backup. 6 orders have lost an hour of changes. |

## What happened

The cleanup job encodes its intent indirectly. What it wants to delete is "a draft the customer abandoned"; what it actually asks for is "a row whose `status` column reads `draft` and whose `updated_at` is more than 90 days old". Those two descriptions agreed for as long as `'draft'` had exactly one meaning.

On 11 August a change introduced `pending_payment` for orders awaiting a bank transfer. To avoid editing many call sites, the author set the database default for `status` back to `'draft'` and had the payment code write `pending_payment` afterwards. The consequence is that `'draft'` became the state an awaiting-payment order passes through, and in any case where the follow-up write did not land, the state it stays in. Bank transfers routinely sit unpaid for well over 90 days before anyone considers them abandoned, so the awaiting-payment population aged straight into the cleanup job's selection window.

The specific design decision that caused the harm is also the one that hid it. The change was structured to avoid touching call sites, which meant no call site appeared in the diff, which meant a reviewer reading that diff had no reason to think about who else reads `status`. The cleanup job was never mentioned in the review because nothing in the change pointed at it.

## Why it was not caught before production

- **The review had no signal to follow.** One reviewer, on a diff that deliberately contained no consumer-side changes. Changes to the meaning of an enum value or to a column default alter the behaviour of every reader of that column, and none of those readers are visible in the diff.
- **Staging cannot express this class of bug.** The environment holds no orders older than 30 days. Every retention rule we operate is keyed on an age threshold of 90 days or more, so no age-triggered defect can reproduce there. This is a structural blind spot, not a gap in test coverage.
- **The job has no dry-run mode.** There is no way to ask what it would delete without deleting it.
- **The job has no blast-radius guard.** A cleanup that normally removes a small trickle of abandoned drafts removed 4,200 rows in four minutes and treated that as an ordinary night.

## Why detection took seven and a half hours

There was no automated detection at any layer. No alert on deletion volume, no alert on a drop in live order count, no per-row logging that would let anyone reconstruct what was removed. The job's only output is a count, and nothing reads it.

Once a human was involved, the delays were procedural rather than technical: 35 minutes from the customer call to escalation, and another 35 minutes to confirm the deletion. Both are reasonable for an unrecognised report, and both are irrelevant next to the seven hours during which the system knew 4,200 rows had vanished and told nobody.

## Recovery

Recovery worked and was the one part of this that behaved as designed. The gap is the one-hour restore granularity, which converted a fully recoverable incident into a partially unrecoverable one for 6 orders. Point-in-time recovery, had it been available, would have brought that number to zero.

## Open questions

The change merged on 11 August but the first bad run was the night of 14 August, and the nightly runs of 12 and 13 August did not delete these rows. The most likely explanation is that the merge did not deploy until 13 August, but nobody has confirmed the deploy timestamp. This matters: if the change was live before 13 August, then our understanding of the mechanism is incomplete and the remediation below may be aimed at the wrong thing. Confirming this is a prerequisite to closing the postmortem.

We also do not know how many of the 4,200 customers noticed. Support saw one call.

## Action items

1. **Confirm the deploy timestamp of the 11 August change** and reconcile it against the 12 and 13 August job runs. Blocks everything below.
2. **Contact the 6 customers whose edits were lost.** Reconstruct what we can from application logs and payment records.
3. **Stop inferring lifecycle from `status`.** Give the cleanup job an explicit signal, such as an `abandoned_at` column set by the code that decides an order is abandoned. Until that exists, change the query to an explicit allowlist of deletable statuses so that a newly introduced status is excluded by default rather than included by default.
4. **Audit for remaining exposure.** Confirm no awaiting-payment orders are currently sitting at `status = 'draft'`, and fix the write-then-update pattern so that an order's status is correct at insert time.
5. **Add soft delete to the orders table**, with a retention window long enough that a customer report can still recover the row.
6. **Add a blast-radius guard to every destructive batch job:** abort and page if the affected row count exceeds a fixed ceiling or a multiple of the trailing median.
7. **Add a dry-run mode and per-row logging.** The job must be able to report the identifiers it would delete, and must record the identifiers it did delete, retained independently of the table.
8. **Alert on live order count.** A step change of this size in a four-minute window should page within minutes, not surface through a telephone call.
9. **Change review policy for schema semantics.** Any change to a column default, an enum's set of values, or the meaning of an existing value requires a second reviewer and an enumerated list of the column's consumers, batch jobs included.
10. **Seed staging with aged data** spanning every retention boundary we operate, so that age-triggered logic is exercisable before production.
11. **Keep the cleanup job disabled** until items 3, 6 and 7 are complete.