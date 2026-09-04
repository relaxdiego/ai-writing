# Postmortem: nightly cleanup deleted 4,200 live orders

**Date of incident:** 14 August 2026
**Duration:** 02:04 (deletion complete) to 13:40 (rows restored), 11 hours 36 minutes
**Detected by:** a customer, by telephone
**Current state:** the cleanup job is disabled and must stay disabled until the open question in the "Reconstruction" section below is settled

## Summary

The nightly cleanup job deleted 4,200 live customer orders that were awaiting bank transfer. The job is meant to delete abandoned draft orders, and it identifies them by `status = 'draft' AND updated_at < now() - 90 days`. A change merged on 11 August added a new status value, `pending_payment`, and arranged for rows to be written as `'draft'` first and updated afterwards, which gave `'draft'` a second meaning the cleanup job did not know about. All 4,200 rows were restored from the 01:00 backup. Changes made to 6 of those orders between 01:00 and 02:00 were lost permanently.

## Impact

Every one of the 4,200 deleted orders was a live order, not an abandoned draft. For roughly eleven and a half hours those orders did not exist: customers looking at their order history saw nothing, and any application write touching one of those rows in that window either failed or silently created a duplicate. We have not quantified how many such writes occurred, and doing so requires the application logs for 02:04 to 13:40.

The 6 orders that were modified between the backup at 01:00 and the deletion at 02:00 came back in their 01:00 state. Whatever those changes were, they are gone, and the customers behind those 6 orders need to be contacted individually rather than covered by a general notice.

One customer called in seven hours. That is not evidence that the deletion went mostly unnoticed; it is evidence that a customer has to be actively looking at an order to notice it has vanished, and that we should not expect a faster call next time.

## Timeline

All times are on 14 August.

| Time | Event |
|---|---|
| 01:00 | Nightly backup taken. This is the snapshot the restore later came from. |
| 02:00 | Cleanup job starts. |
| 02:04 | Job finishes, having deleted 4,200 rows. It logs a count and nothing else. No alert fires. |
| 09:20 | A customer telephones support to ask why their order has disappeared. |
| 09:55 | Support escalates to engineering. |
| 10:30 | An engineer confirms the deletion. |
| 10:35 | Cleanup job disabled. It remains disabled. |
| 13:40 | All 4,200 rows restored from the 01:00 backup. |

The deletion went undetected for 7 hours 16 minutes, and unconfirmed for 8 hours 26 minutes. Recovery took 3 hours 10 minutes from confirmation, which is the one part of the response that worked roughly as it should have.

## Cause

The cleanup job does not know which orders are abandoned. It infers abandonment from a column that describes something else. `status` records where an order sits in its lifecycle, and the job treats one value of that column, `'draft'`, as a proxy for "nobody will ever come back to this, so it is safe to destroy". That inference held only for as long as `'draft'` had exactly one meaning.

The 11 August change gave it a second one. Rather than update the call sites that create orders, the author set the column default back to `'draft'` and had the payment code write `pending_payment` afterwards, so `'draft'` came to mean both "a customer's unfinished draft" and "a row whose payment state has not been applied yet". Nothing in the change touched the cleanup job, and nothing in the system connects a new value in the status vocabulary to the code that reads status and acts destructively on it.

The severity of the outcome comes from the deletion being a hard `DELETE` on a table with no soft delete, executed by a job with no dry-run mode, which logs only a count of what it removed. Even after the job was known to be at fault, we could not say from its own output which rows it had taken; that had to be reconstructed from the backup.

## Reconstruction: one part of this does not add up

The account above is how the change was intended to work, but it does not explain the rows we actually lost, and this needs to be settled before the job runs again.

The change merged on 11 August. The job ran on 14 August and deleted rows whose `updated_at` was more than 90 days in the past. A row created under the new scheme cannot be three days old and ninety days stale at the same time, so the 4,200 deleted rows were not rows created since the change. They already existed, and something around 11 August set their `status` to `'draft'` while leaving `updated_at` untouched. Before that they must have carried some other value, because the cleanup job had been running nightly against them for months without deleting them.

The leading hypothesis is that the migration that changed the column default also rewrote `status` on existing rows, either as a backfill of nulls or as an explicit update, and that it did so in SQL that bypassed whatever normally maintains `updated_at`. Those rows would have kept their original stale timestamps and become eligible for deletion the moment the migration committed, with the first nightly run after that taking all of them at once. A single run removing 4,200 rows is consistent with a one-off eligible population rather than a steady daily trickle.

Four pieces of evidence settle it:

- the migration's DDL and any DML that shipped alongside it
- whether `updated_at` is maintained by the application or by a database trigger
- the `created_at` range and age distribution of the 4,200 restored rows
- whether 4,200 matches the count of orders that were awaiting bank transfer before 11 August

If the hypothesis is wrong and these were genuinely recent rows, then the age predicate itself is broken, the blast radius is larger than one status value, and the fix is a different one. Re-enabling the job on the strength of a plausible story rather than a confirmed one risks fixing the wrong thing.

## Why nothing caught it

Review did not catch it because the change was read as a change to how orders are created, and its effect on a consumer elsewhere in the system was never raised. One reviewer looked at it, and the cleanup job was not mentioned. There is no mechanism, automated or procedural, that surfaces the readers of a column when someone adds a value to it.

Staging could not have caught it. The environment holds no orders older than 30 days, so a rule with a 90-day threshold has nothing to match there. Any job whose predicate is an age threshold is untestable in an environment whose data is younger than that threshold, and this is true of the whole class of cleanup jobs, not just this one.

Monitoring did not catch it because there is none. The job deleted roughly two orders of magnitude more rows than a normal night and reported the number to a log that nobody reads at 02:04. The count needed to detect this was already being computed; it simply had nowhere to go.

## Actions

We do not yet have owners or dates against these. Assigning them is the first thing to do with this document.

Before the cleanup job is re-enabled:

1. Answer the open question in the Reconstruction section, using the four pieces of evidence listed there. This gates everything else.
2. Make the job fail closed on any `status` value it does not recognise. If it encounters a value outside the set it was written against, it should abort and alert rather than proceed on the values it does understand.
3. Add a dry-run mode and a magnitude guard: the job aborts and alerts if the candidate set exceeds a fixed ceiling or some multiple of the trailing median, and a human approves the run before it proceeds.
4. Log the primary key of every row deleted, not a count. Recovery should never again depend on diffing against a backup to find out what was lost.

Within the next cycle:

5. Add soft delete with a retention window to the orders table, so that a bad run is reversible in minutes and without a restore.
6. Alert on the job's deletion count to on-call, with a threshold set from the historical nightly distribution.
7. Contact the 6 customers whose orders lost an hour of changes, and reconstruct what was lost where it can be reconstructed from application logs.
8. Quantify the failed and duplicated writes against the missing rows between 02:04 and 13:40, and correct whatever that turns up.

Structural, and the reason this class of incident will recur if we stop at the items above:

9. Give staging aged data, or provide a way to test age-threshold logic against a controllable clock. Without one of the two, no cleanup job in this system is testable before it runs against production.
10. Require that any change adding a value to a shared enum name the code that reads that column, and route review to the owners of the destructive readers. `'draft'` was load-bearing for a job three subsystems away, and nothing made that visible to the person changing it.