# Incident postmortem: nightly cleanup job deleted 4,200 live orders

**Status:** resolved, data restored. The cleanup job remains disabled and must not be re-enabled until the blocking action below is closed.

## Summary

On 14 August the nightly draft-order cleanup job deleted 4,200 live customer orders that were awaiting payment by bank transfer. The job is intended to delete abandoned draft orders older than 90 days, and it deleted these rows because they carried `status = 'draft'` and had not been touched in more than 90 days. All 4,200 rows were restored from the 01:00 backup by 13:40 on the same day. Six orders lost the changes made to them between 01:00 and 02:00; those changes are not recoverable from any source we hold.

The deletion was permanent at the moment it ran. There is no soft delete on the orders table, the job logs only a count and not the rows it touched, and it has no dry-run mode, so the incident was invisible internally and had to be reported to us by a customer.

## Impact

Affected customers had a paid-for or in-progress order vanish from their account for eleven hours and thirty-six minutes, between 02:04 and 13:40. Because the job logged only a count, we cannot reconstruct which customers loaded the site during that window and saw nothing; one telephoned support and the rest are unknown to us. Six orders were restored to their 01:00 state and are silently one hour stale, which means any customer or agent edit made in that hour has been reverted without notice to either party.

## Timeline

All times are on 14 August as reported.

| Time | Event |
|---|---|
| 02:00 | Nightly cleanup job starts. |
| 02:04 | Job finishes. 4,200 live orders deleted. |
| 09:20 | A customer telephones support asking why their order has disappeared. |
| 09:55 | Support escalates to engineering. |
| 10:30 | An engineer confirms the rows were deleted by the cleanup job. |
| 10:35 | Cleanup job disabled. |
| 13:40 | All 4,200 rows restored from the 01:00 backup. Six orders restored to a stale state. |

Detection took seven hours and twenty minutes from the start of the job, and depended entirely on a customer choosing to call. Once escalated, engineering confirmed the cause in thirty-five minutes and restored in a further three hours and ten minutes, which is the part of the response that worked.

## What happened

The cleanup job selects rows where `status = 'draft'` and `updated_at < now() - 90 days`, and deletes them outright. Its correctness rests on a single assumption: that `'draft'` means abandoned-and-worthless, and that nothing else in the system uses that value to mean anything else.

On 11 August a change was merged introducing a new status, `pending_payment`, for orders awaiting a bank transfer. Rather than update every call site that creates an order, the author set the database default for `status` back to `'draft'` and had the payment code write `pending_payment` in a second statement after the row was inserted. That decision put `'draft'` back into the position of being the value a row holds when nobody has said otherwise, at the same time as the system acquired a legitimate, long-lived, non-abandoned state that a row could be sitting in. Bank transfers routinely take longer than 90 days to be given up on, so an awaiting-payment order is exactly the kind of row that ages past the cleanup threshold without anything being wrong with it.

The two changes are individually reasonable and jointly destructive. Neither author was in a position to see the other: the cleanup job was not mentioned in the review of the `pending_payment` change, and the cleanup job's own predicate had been correct for as long as it had existed.

## What we do not yet know

The account above explains why an awaiting-payment order can end up matching the cleanup query. It does not yet explain the population of 4,200. The change merged on 11 August, three days before the incident, and the deleted rows had `updated_at` older than 90 days, so they must have existed and been untouched since well before the change. Something was previously keeping those rows out of the cleanup job's reach, and the 11 August change stopped it. Candidate explanations we should test against the restored data and the 11 August diff:

- Those rows previously held a status other than `'draft'` and were rewritten to `'draft'` by the new default or by a backfill, without `updated_at` being advanced.
- Those rows were previously being touched periodically by a write path that the change removed or bypassed, so their `updated_at` had been kept fresh.
- The cleanup query itself was altered by the change, or by an earlier one, in a way not yet identified.

Until we know which of these is true, we do not know the true blast radius, we cannot say the job is safe to re-enable, and we cannot rule out other tables or jobs sitting behind the same mechanism. Resolving this blocks everything else.

## Why nothing stopped it

Four separate defences were absent rather than defeated, which is worth stating plainly: none of them failed, because none of them existed.

Review did not catch the interaction because a status-value change was reviewed as a status-value change. One reviewer read a diff that touched the schema default and the payment code, and there was nothing in the diff to point at a batch job living somewhere else in the repository that keys off the same column. Staging could not have caught it either: staging holds no orders older than 30 days, so the 90-day predicate cannot match anything there, and the entire class of bug that depends on data age is invisible in that environment by construction.

The job's own design removed every chance to catch the problem at run time or shortly after. With no dry-run mode, nobody could have inspected the delete set before it executed. With only a count logged, the 02:04 log line recorded a number that nobody was watching and that would not have looked alarming without a baseline to compare it against. With no soft delete, the rows were gone rather than flagged, which turned a reversible mistake into a restore-from-backup operation and cost six orders an hour of real customer data.

## Action items

**Blocking, before the job is re-enabled.** Determine the actual mechanism by which 4,200 rows aged past 90 days as `'draft'`, using the restored rows and the 11 August diff. Confirm from that whether any other table or job depends on the same mechanism.

**Contact the six affected customers.** Their orders are silently one hour stale. Identify what changed between 01:00 and 02:00 from application logs where possible, and tell them regardless.

**Fail closed on unknown statuses.** Change the cleanup job to delete only statuses on an explicit allow-list, and to abort with an alert if it encounters a status value it does not recognise. A new status should stop the job, not be swept up by it.

**Add a volume guard.** The job should refuse to run and alert if its candidate set exceeds a multiple of its trailing median. A jump to 4,200 rows would have stopped it at 02:00.

**Add a dry-run mode and per-row logging.** Log the primary keys of every row before deleting it, with retention long enough to reconstruct an incident. The dry-run mode should be runnable against a production replica.

**Add soft delete to the orders table**, with a retention window, so that recovery is a flag flip rather than a restore that rolls back an hour of unrelated work.

**Remove the write-then-update pattern for `status`.** Set the status in the insert, and remove the database default or point it at a value no cleanup job acts on. A column whose correct value arrives in a second statement will be wrong for some rows permanently.

**Extend the review checklist for status and enum changes** to require enumerating every consumer of that column, including scheduled and batch jobs, and to name them in the review.

**Seed aged fixtures in staging**, or accept that staging cannot test age-dependent logic and route that testing to dry runs against a replica instead. The current state, where staging looks like a test environment but structurally cannot exercise this class of job, is the more dangerous of the two.

**Give support a runbook entry for "customer reports a missing order"** that escalates to engineering immediately rather than through normal triage. Thirty-five minutes elapsed between the call and the escalation while data loss was ongoing and unbounded.