# Postmortem: cleanup job deleted 4,200 live orders

**Date of incident:** 14 August 2026
**Status:** Resolved, with the cleanup job disabled pending remediation
**Author:** Mark Maglana

## Summary

A nightly cleanup job whose purpose is to delete abandoned draft orders deleted 4,200 live customer orders that were awaiting bank transfer payment. The orders were invisible to customers for eleven and a half hours. All 4,200 rows were restored from backup, but because the restore point was an hour before the deletion, 6 orders permanently lost changes made in that hour. Nobody at the company noticed: detection was a customer telephoning support seven hours after the fact.

The trigger was a change merged on 11 August that introduced a `pending_payment` status. The cause of the damage was that the cleanup job treats `status = 'draft'` as proof of abandonment, deletes hard rather than soft, logs only a count, and had no threshold that would stop it from deleting 4,200 rows in one run.

## Timeline

All times on 14 August unless stated.

| Time | Event |
|---|---|
| 11 Aug | Change introducing `pending_payment` merged. Deploy date not yet established. |
| 02:00 | Nightly cleanup job starts. |
| 02:04 | Job finishes. 4,200 live orders deleted. No alert fires. |
| 09:20 | A customer telephones support asking why their order has disappeared. |
| 09:55 | Support escalates to engineering. |
| 10:30 | Engineer confirms the deletion. |
| 10:35 | Cleanup job disabled. |
| 13:40 | 4,200 rows restored from the 01:00 backup. |

Seven hours and sixteen minutes passed between the deletion and any human noticing it, and the human who noticed was a customer. Once the report reached support, another thirty-five minutes passed before it reached an engineer. From the point an engineer looked at it, containment took five minutes and the restore took three hours and ten minutes.

## What happened

The cleanup job selects rows where `status = 'draft'` and `updated_at < now() - 90 days`, and deletes them. That query encodes an assumption that was true when it was written and is no longer true: that a draft order untouched for 90 days has been abandoned by its customer.

The 11 August change introduced `pending_payment` for orders awaiting a bank transfer. To avoid modifying the many call sites that create orders, the author left the database default for `status` as `'draft'` and had the payment code set `pending_payment` after the row was written. This was a reasonable local decision. Its consequence was not local: it meant that an order's status column is not authoritative at the moment the row is created, and that any order whose follow-up write does not happen remains a draft indefinitely. Bank transfers routinely sit unpaid for more than 90 days without being abandoned, so the population of legitimately-live orders carrying `status = 'draft'` and an old `updated_at` was large.

One part of the mechanism is not yet established, and we should not close this document claiming otherwise. Rows more than 90 days old on 14 August were created before 16 May, three months before the change was merged, so the new code path cannot have created them. Something in the 11 August change must have caused a large set of pre-existing rows to match a query they had not matched on 12 or 13 August. The candidates are a deploy that happened later than the merge, a migration or backfill that rewrote the status of existing awaiting-payment orders, or a code path that rewrites status when an order is read or updated. We cannot distinguish between these from the job's own output, because it logs a count and nothing else. Determining which one it was is the first action item, and the remediation for the job itself does not depend on the answer.

## Contributing factors

These are properties of the system that turned a schema change into eleven hours of missing customer data. Each of them independently would have reduced the severity.

- **The job hard-deletes.** There is no soft delete on the orders table, so recovery required a restore from backup rather than an UPDATE, which is what turned a five-minute fix into a three-hour one and is the sole reason 6 orders lost data.
- **The job logs a count, not identities.** The engineer at 10:30 could see that 4,200 rows had gone but not which ones. This blocked both the incident response and the subsequent investigation.
- **The job has no dry-run mode.** There was no way to ask what it would delete before it deleted it, and no way to run it safely against production data.
- **There is no volume threshold or alert.** A nightly job that normally deletes a handful of rows deleted 4,200 and completed without complaint. This is the single cheapest control we were missing.
- **The review had no path to the consumer.** The change was reviewed by one person and the cleanup job was not raised. Nothing in the process connects a change to the meaning of `status` with the batch jobs that read `status`, so the reviewer had no way to know the question needed asking.
- **Staging cannot express this bug.** Staging holds no orders older than 30 days, so a defect that requires a 90-day-old row is undetectable there by construction. Any time-dependent job is currently untested.
- **Customer-facing disappearance is not monitored.** 4,200 customers lost sight of their orders and one of them reached us.

## Open questions

Each of these needs an answer before the job is re-enabled.

1. What in the 11 August change caused pre-existing rows to match on 14 August but not on 12 or 13 August, and when was that change actually deployed?
2. Was 4,200 the complete matching set, or did the four-minute run stop early? If more rows matched, more rows are still at risk.
3. What happened to reads and writes against the 4,200 deleted rows between 02:04 and 13:40? Failed writes are recoverable; writes that created replacement or duplicate records are not, and the restore may have collided with them.
4. Did the restore overwrite legitimate state beyond the 6 orders already identified?
5. Why did only one affected customer reach support? If the other 4,199 tried a channel that did not escalate, our detection gap is worse than this incident showed.

## Action items

Owners still need to be assigned. The cleanup job stays disabled until the four items marked P0 are in production.

| Action | Class | Priority |
|---|---|---|
| Answer open question 1 and confirm the deployed mechanism | Investigate | P0 |
| Add soft delete to the orders table; cleanup sets `deleted_at`, a separate reaper hard-deletes after a 30-day retention window | Mitigate | P0 |
| Log the identifier of every row the job deletes | Detect | P0 |
| Abort the job and page if the candidate set exceeds a volume threshold, rather than only alerting after the fact | Detect | P0 |
| Stop inferring abandonment from `status = 'draft'`; require an explicit abandonment marker written by the code that abandons an order, and exclude any order with an associated payment intent | Prevent | P0 |
| Set the correct status in the initial insert rather than writing `draft` and correcting it afterwards | Prevent | P1 |
| Add a dry-run mode and make it the default in every environment except the scheduled production run | Mitigate | P1 |
| Require a reviewer from the team owning batch jobs on any change to `status` values or the orders schema, with a checklist item enumerating consumers of the column | Prevent | P1 |
| Seed staging with aged order fixtures, or support a clock offset in tests, so time-dependent jobs are testable | Prevent | P1 |
| Enable point-in-time recovery on this database so a restore does not cost an hour of writes | Mitigate | P1 |
| Alert on the population counts of `draft` and `pending_payment` orders | Detect | P2 |
| Add a support runbook entry for "customer reports missing order" that escalates to engineering immediately | Detect | P2 |

## Note on blame

The author of the 11 August change made a defensible engineering trade: avoid touching many call sites, accept a two-step write. The information that would have made that trade look wrong lived in a batch job they had no reason to read and no mechanism to be shown. The reviewer had the same blind spot. The failure being corrected here is that the meaning of a column can be changed without any of its consumers being consulted, and that when a consumer then behaves catastrophically, it does so quietly, irreversibly, and without recording what it did.