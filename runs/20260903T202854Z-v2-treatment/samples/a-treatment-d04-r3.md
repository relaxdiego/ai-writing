# Postmortem: nightly cleanup deleted 4,200 live orders

On 14 August the nightly cleanup job deleted 4,200 live customer orders that were awaiting bank transfer. All 4,200 rows were restored from backup by 13:40 the same day. Six of them lost changes made between 01:00 and 02:00, which are not recoverable from any source we hold. Detection was by a customer telephone call more than seven hours after the deletion; we had no internal signal at all.

## Impact

4,200 orders were absent from the system for between 9 and 11.5 hours, depending on when each was queried. Customers who looked during that window saw their order gone with no explanation, and at least one of them called us. Six orders were restored to their 01:00 state rather than their 02:00 state, so any customer or agent edit made in that hour is silently lost; those six need to be identified and their owners contacted. The cleanup job has been disabled since 10:35 on 14 August and remains disabled, so abandoned drafts are now accumulating.

## Timeline (14 August)

| Time | Event |
| --- | --- |
| 02:00 | Cleanup job starts |
| 02:04 | Job finishes, having deleted 4,200 rows; logs a count only |
| 09:20 | Customer telephones support to ask why their order has disappeared |
| 09:55 | Support escalates (35 minutes) |
| 10:30 | Engineer confirms the deletion (35 minutes) |
| 10:35 | Cleanup job disabled |
| 13:40 | Rows restored from the 01:00 backup |

## What happened

The cleanup job deletes rows where `status = 'draft'` and `updated_at < now() - 90 days`. It rests on an invariant that was never written down anywhere: that `draft` means an order the customer started and abandoned, and nothing else.

On 11 August a change introduced `pending_payment` for orders awaiting a bank transfer. To avoid touching many call sites, the author left the database default for `status` as `'draft'` and had the payment code set `pending_payment` after the row was written. The effect is that `draft` is now also the state every order passes through on the way to payment, and the state an order stays in if the follow-up write does not happen. Orders awaiting a bank transfer routinely sit for more than 90 days without being abandoned, so an order in that condition satisfies both halves of the cleanup predicate and is indistinguishable, to the query, from a draft nobody ever came back to.

## What we do not yet know, and must establish first

The deleted rows all had `updated_at` older than 14 May, which is before the `pending_payment` change was merged. The change on 11 August therefore cannot by itself account for their status: these orders were already stored as `draft` while awaiting payment, and the change did not backfill them. If that reading is right, the same predicate would have matched on earlier nights too, and we have no way to see it from the job's own output, because it logs a count and not identities.

Before anything else, we need to compare the last several nights of backups and determine whether runs before 14 August also deleted live orders. Everything below is written assuming they did not; if they did, the incident is larger than this document describes and the recovery work is not finished.

## Why nothing caught it

The change was reviewed by one person and the cleanup job was not raised. Nothing in the review process connects a change in the meaning of a column to the scheduled jobs that read it, and there is no way to discover that connection short of knowing it already.

Staging could not have surfaced the interaction. It holds no orders older than 30 days, so the 90-day predicate matches nothing there and the job appears to work correctly for the same reason it appears to work correctly on an empty table.

Detection depended on a customer noticing. We have no alerting on deletion volume, so a job that deleted 4,200 rows instead of its usual number produced no signal. Once the customer did call, another 70 minutes went to escalation and confirmation.

## Actions

1. Diff the backups for the nights preceding 14 August and confirm whether earlier runs deleted live orders. Blocks everything else.
2. Identify the six orders whose 01:00–02:00 changes were lost, and contact the affected customers.
3. Keep the job disabled until it logs the primary key of every row it deletes, supports a dry-run that writes the same log without deleting, and aborts when the candidate count exceeds a threshold rather than proceeding.
4. Add soft delete to the orders table with a retention window, so that the next occurrence is a reversible update rather than an 11.5-hour restore.
5. Stop inferring abandonment from `status`. Record it explicitly, for example an `abandoned_at` column set by the code path that actually observes abandonment, and have cleanup key on that.
6. Backfill existing awaiting-payment orders to `pending_payment` so the two meanings of `draft` are separated in the data and not only in new writes.
7. Alert on deletion volume per job, by absolute count and by deviation from the trailing average.
8. Add to the review checklist: any change to the set or meaning of values in a status column must enumerate the consumers of that column, scheduled jobs included, and the review must record that enumeration.
9. Seed staging with aged data, or run the job in dry-run against production and read the log, so that time-dependent predicates can be exercised before they run for real.