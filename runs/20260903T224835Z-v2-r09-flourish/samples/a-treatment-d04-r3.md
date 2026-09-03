# Postmortem: nightly cleanup job deleted 4,200 live customer records

**Date of incident:** 14 August · **Status:** mitigated, cleanup job disabled · **Data loss:** 6 orders

## Summary

The nightly draft-order cleanup job ran at 02:00 on 14 August and deleted 4,200 rows that were not abandoned drafts but live customer orders awaiting payment. The job deletes rows matching `status = 'draft' AND updated_at < now() - 90 days`, and orders awaiting a bank transfer were carrying `status = 'draft'` while sitting untouched for longer than 90 days, so they satisfied both halves of the predicate. Nobody at the company noticed. Detection came from a customer who telephoned support at 09:20 to ask where their order had gone, seven hours and sixteen minutes after the deletion completed. All 4,200 rows were restored from the 01:00 backup by 13:40. Because the backup predates the deletion by an hour, any change written between 01:00 and 02:00 was lost, which affected 6 orders. Those 6 need manual reconciliation.

## Timeline

| Time (14 Aug) | Event |
| --- | --- |
| 02:00 | Cleanup job starts. |
| 02:04 | Job finishes. 4,200 rows deleted. Job logs the count only; no record of which rows. |
| 09:20 | Customer telephones support asking why their order has disappeared. |
| 09:55 | Support escalates to engineering. |
| 10:30 | Engineer confirms the rows were deleted by the cleanup job. |
| 10:35 | Cleanup job disabled. It remains disabled. |
| 13:40 | All 4,200 rows restored from the 01:00 backup. |

Note the earlier date that matters: on 11 August a change was merged introducing the `pending_payment` status for orders awaiting a bank transfer.

## Cause

The 11 August change added `pending_payment` as a new status value. Rather than update the call sites that create orders, the author set the database default for `status` back to `'draft'` and had the payment code issue a second write setting `pending_payment` after the row already existed. This makes `draft` the status of record for a bank-transfer order during the window between the two writes, and it makes the correct status depend on a follow-up statement rather than on the insert itself. The cleanup job, written months earlier against an assumption that `draft` means abandoned, was not consulted and was not mentioned in the review.

One part of this chain does not close on the facts we have, and it needs to be settled before we act on the rest. Rows deleted on 14 August had `updated_at` older than 14 May, which is three months before `pending_payment` existed. A row created after the 11 August merge cannot have been older than 90 days on 14 August, so the deleted rows were not created by the new code path. Two explanations fit, and they call for different fixes. Either bank-transfer orders predate the change, were always stored as `draft`, and the cleanup job has been mis-scoped since it was written, in which case 11 August is not the cause and we should expect earlier deletions in the job's historical counts. Or the 11 August change touched existing rows in a way that left them as `draft` without advancing `updated_at`, through a migration or a backfill, in which case the deploy is the trigger. The restored rows are the evidence: their `status` and `updated_at` values, read against the deploy time, distinguish the two cases. Until that check is done, treat the causal account above as provisional.

Independent of which explanation holds, the underlying defect is the same. A destructive job identified its targets by a status value that was never a reliable signal of abandonment, and no part of the system required that assumption to be restated or checked when the meaning of the status changed.

## Contributing factors

Several conditions turned a wrong query into 4,200 lost records and an eight-hour outage.

The change was reviewed by one person, and the review considered the new feature without asking what else reads `status`. A grep for readers of that column would have found the cleanup job.

Staging could not have surfaced the interaction. It holds no orders older than 30 days, so a bug that requires a 90-day-old row is invisible there by construction. Any test that would have caught this had to be written deliberately, and none was.

The job has no dry-run mode, so there was no way to see the row set before deleting it and no habit of doing so. It logs a count and nothing else, so after the fact we could not say which records had gone without diffing against a backup. There is no soft delete on the table, so the deletion was immediately irreversible in place and recovery required a restore.

Nothing alerted. A job that normally removes a handful of stale drafts removed 4,200 rows and the count went into a log that no one reads. Detection depended on a customer noticing and choosing to telephone rather than assume the site was broken, and we have no way to know how many affected customers did not call.

## Actions

- Confirm the mechanism against the restored rows before closing this postmortem, and check the job's historical deletion counts for earlier spikes.
- Reconcile the 6 orders that lost changes between 01:00 and 02:00, and contact those customers.
- Rewrite the cleanup predicate to select on an explicit, positively-set abandonment marker rather than on the absence of a status the job does not know about. An allowlist of statuses is safer than the current implicit assumption, but a dedicated column is better than either.
- Add soft delete to the orders table, with a retention window long enough to cover a weekend, before the cleanup job is re-enabled.
- Add a dry-run mode and per-row logging of primary keys to the job, and require a dry-run diff to be reviewed before any change to its query ships.
- Add a deletion ceiling to the job: abort and alert if a run would delete more than a threshold, rather than proceeding.
- Alert on the deletion count itself, routed to an on-call channel rather than a log file.
- Seed staging with orders spanning the age ranges the production data actually contains, including rows older than 90 days.
- Require any change to an enum or status column to name the readers of that column in the pull request description, and treat destructive batch jobs as requiring a second reviewer.

The cleanup job stays disabled until the predicate is rewritten, soft delete is in place, and the deletion ceiling and alert are live. The backlog of genuinely abandoned drafts is not urgent and can wait.