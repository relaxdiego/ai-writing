# Postmortem: nightly cleanup job deleted 4,200 live orders

**Date of incident:** 14 August · **Status:** mitigated, cleanup job disabled · **Data loss:** partial, 6 orders

## Summary

A nightly cleanup job deleted 4,200 live customer orders between 02:00 and 02:04 on 14 August. The job is meant to delete abandoned drafts, which it identifies as rows with `status = 'draft'` that have not been updated in 90 days. A change merged on 11 August introduced a `pending_payment` status for orders awaiting a bank transfer, left the database default for `status` as `'draft'`, and relied on the payment code to move rows out of that state after the row was written. Orders awaiting a bank transfer therefore sat under a status the cleanup job reads as abandoned, and bank transfers routinely take longer than 90 days to give up on. All 4,200 rows were restored from the 01:00 backup by 13:40. Six orders permanently lost changes written between 01:00 and 02:00. The job has been disabled since 10:35 and should stay disabled until it has a dry-run mode, per-row logging and a volume guard.

## Impact

4,200 order rows were deleted and were absent from customer accounts for roughly eleven and a half hours. The number of distinct customers behind those rows is not yet known, because the job logs only a count and not the rows it touches; the identity of the deleted set had to be reconstructed by comparing the live table against the 01:00 backup, and any answer about who was affected has to be derived from the restored data rather than from the job's own output.

Six orders had changes written in the hour between the backup and the deletion, and those changes are not recoverable from the backup. They need to be identified from application logs and reconciled by hand with the customers concerned. We do not yet know what the lost writes were, so we cannot say whether any of them were payments, address changes or cancellations, and the six customers should be contacted regardless.

At least one customer noticed and called. We have no way to tell from our own systems how many others saw a missing order and did not call, or what downstream effects the deletion had during the window: cancellation emails, payment provider reconciliation and any webhook consumers all need checking for actions taken against rows that no longer existed.

## Timeline

All times on 14 August unless stated. Elapsed is time since the previous row.

| Time | Event | Elapsed |
|---|---|---|
| 11 Aug | Change introducing `pending_payment` merged, reviewed by one person | |
| 02:00 | Nightly cleanup job starts | |
| 02:04 | Job finishes, 4,200 rows deleted, count logged, no alert | 4m |
| 09:20 | Customer telephones support asking why their order has disappeared | 7h 16m |
| 09:55 | Support escalates | 35m |
| 10:30 | Engineer confirms the deletion | 35m |
| 10:35 | Cleanup job disabled | 5m |
| 13:40 | 4,200 rows restored from the 01:00 backup | 3h 5m |

Time from the deletion completing to a customer-initiated report was 7 hours 16 minutes. Time from that report to engineering confirmation was 1 hour 10 minutes. Time from confirmation to restore was 3 hours 5 minutes.

## How it happened

The cleanup query treats the combination of `status = 'draft'` and ninety days without an update as a proxy for "a customer started an order and walked away". That proxy was sound while `draft` had one meaning, namely an order that had not been submitted. The 11 August change gave the value a second meaning. To avoid updating a large number of call sites, the author kept `'draft'` as the database default and had the payment code write `pending_payment` afterwards, so an order waiting on a bank transfer passes through, and can rest in, the state the cleanup job reads as abandoned. Ninety days is short relative to how long a bank transfer takes to be given up on, so the newly included population does not merely brush against the threshold, it routinely exceeds it. The job did not misfire on an edge case. It found a class of live orders and would have found a fresh cohort of them every night it ran.

Nothing connected the two pieces of code. The payment path and the cleanup job share no functions, no module and no test; they share a column. The schema records that `status` exists but not that one of its values plus a timestamp is load-bearing for an irreversible delete, so a reviewer looking at the payment change had nothing in front of them pointing at the consumer. The design choice that caused the incident, keeping the default and mutating after write, is an ordinary instinct for limiting the blast radius of a change, and the failure here is that the system gave nobody a way to see what that choice touched.

Staging could not have surfaced it. The interaction only appears in rows older than ninety days and staging holds no orders older than thirty, so the environment we would normally point at for this class of bug was structurally incapable of reproducing it.

## Contributing factors

- **No dry-run mode.** The job cannot be asked what it would delete. There was no cheap way for the author of the `pending_payment` change, or the reviewer, to check the interaction even had they thought of it.
- **No per-row logging.** The job logs a count. Reconstructing the affected set required a backup diff, which added time to the response and still leaves us unable to say authoritatively what was deleted on earlier nights.
- **No soft delete on the orders table.** Recovery had to go through a backup restore, which is why the one hour recovery-point gap exists and why six orders lost data. A soft delete would have made the incident a flag update.
- **No volume guard or count alerting.** The count was logged and 4,200 looked to the system exactly like any other night. A threshold on rows deleted, absolute or as a fraction of the table, would have stopped the job or paged someone at 02:04 rather than leaving detection to a customer at 09:20.
- **Single reviewer with no view of column consumers.** The review covered the change in front of it. Widening the set of values that can occupy a status column changes the meaning of every query that filters on it, and nothing in the process asks for those queries to be listed.
- **Staging holds no aged data.** Any bug whose trigger is row age is invisible there.
- **Support escalation took 35 minutes.** A report of the form "my data has disappeared" is a potential data-loss incident and does not currently have a fast path.

## Open questions

These are not answered yet and the account above should be treated as provisional until they are.

1. **Why the night of 14 August and not 12 or 13 August?** The change merged on 11 August, the job runs nightly, and the first known destructive run was three nights later. We have the merge time but not the deploy time, and we have not examined the counts logged by the two intervening runs. Until that is done we cannot rule out that rows were deleted on earlier nights and never noticed.
2. **How did rows older than ninety days come to hold `status = 'draft'`?** Any row that was ninety days old on 14 August was created well before `pending_payment` existed, so the post-write mutation in the payment code cannot be what put those particular rows into the deleted set. If a migration or backfill moved existing awaiting-payment orders to `draft`, that migration is part of the cause and is missing from the account above. This needs to be established from the change itself before we call the mechanism understood.
3. **How many distinct customers were affected, and did all 4,200 rows restore correctly?** The restored set should be verified against the backup row for row, not just by count.
4. **What else reads `status = 'draft'`?** Reporting, exports, dunning and any other scheduled job need auditing for the same widened-meaning assumption. The cleanup job is the one that deleted rows; it is unlikely to be the only consumer that was silently redefined.
5. **What acted on the deleted rows during the window?** Emails, webhooks and payment provider reconciliation all need checking for the eleven and a half hour period.

## Action items

Owners and dates are unassigned and need to be allocated. The first item is a precondition for re-enabling the job at all.

- **Keep the cleanup job disabled** until it has a dry-run mode that reports its candidate set, per-row logging of what it deletes, and an abort if the candidate count exceeds a configured threshold.
- **Stop inferring abandonment from status and age.** Have the application set an explicit `abandoned_at` when an order is genuinely abandoned, and have the job delete on that column. The current query re-derives a business decision from two fields that other code is free to change.
- **Add soft delete to the orders table** so that a mistaken delete is recoverable without a restore and without a recovery-point gap.
- **Alert on deletion volume** for this job and for any other scheduled destructive job, so that an anomalous night pages an engineer rather than being noticed by a customer seven hours later.
- **Audit every consumer of `status`** and record, in the schema or alongside it, which values are relied on by destructive or customer-visible queries.
- **Add a review requirement** that any change widening the domain of a status or enum column lists the queries that filter on it, with the destructive ones called out.
- **Seed staging with aged order fixtures** covering the ranges the cleanup rules care about, so age-triggered behaviour is reproducible before production.
- **Give support a fast path for suspected data loss**, so a report of missing records reaches an engineer in minutes rather than in thirty-five.
- **Contact the six customers** whose 01:00 to 02:00 changes were lost, after reconstructing what those changes were from application logs.