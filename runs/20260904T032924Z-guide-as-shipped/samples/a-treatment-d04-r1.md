# Postmortem: nightly cleanup job deleted 4,200 live orders

**Incident date:** 14 August 2026
**Severity:** High. Customer-visible data loss, partially permanent.
**Current status:** Cleanup job disabled since 14 August 10:35. It must stay disabled until the open question below is answered.

## Summary

The nightly draft-order cleanup job ran at 02:00 on 14 August and deleted 4,200 live customer orders in four minutes. The job is meant to delete abandoned draft orders, and it identifies them as rows where `status = 'draft'` and `updated_at` is more than 90 days old. The deleted rows were orders awaiting a bank transfer, which routinely sit untouched for longer than 90 days and which the query could not distinguish from abandoned drafts. Nothing inside the company noticed: no alert fired, and the job's only output is a count of rows deleted. A customer telephoned support at 09:20 asking why their order had disappeared, and an engineer confirmed the deletion at 10:30. All 4,200 rows were restored from the 01:00 backup by 13:40. Six of them lost the changes made between 01:00 and the deletion, and those changes are unrecoverable.

## Impact

The orders were absent for 11 hours and 36 minutes, from 02:04 to 13:40, during a full business morning. Any customer or agent who looked at one of those 4,200 orders during that window saw it as nonexistent rather than as degraded or delayed. Six orders were restored to their 01:00 state, silently discarding an hour of writes; we do not currently know what those writes were, because the job logs no row identifiers and the deleted rows were gone before anyone read them. Every affected order needs to be checked against payment records before we can assert that no bank transfer was received against an order we then destroyed.

## Timeline

| Time (14 Aug unless noted) | Elapsed since deletion | Event |
| --- | --- | --- |
| 11 Aug | — | Change merged introducing `pending_payment`; reviewed by one person; cleanup job not discussed |
| 02:00 | — | Cleanup job starts |
| 02:04 | 0:00 | Job finishes; 4,200 live orders deleted; count logged, no row identifiers |
| 09:20 | 7:16 | Customer telephones support to report a missing order |
| 09:55 | 7:51 | Support escalates to engineering |
| 10:30 | 8:26 | Engineer confirms the deletion and identifies the cleanup job |
| 10:35 | 8:31 | Cleanup job disabled |
| 13:40 | 11:36 | 4,200 rows restored from the 01:00 backup; 6 orders lose one hour of writes |
| ongoing | — | Job remains disabled |

Detection consumed 7 hours 16 minutes and depended entirely on a customer noticing. Triage consumed a further 70 minutes, split evenly between support holding the report and engineering confirming it. Once the cause was identified the response was fast: five minutes to disable the job, three hours to restore.

## Mechanism

The change merged on 11 August added `pending_payment` as a status for orders awaiting a bank transfer. Rather than update the many call sites that create orders, the author left the database default for `status` as `'draft'` and had the payment code issue a second write setting `pending_payment` after the row was inserted. This makes `'draft'` do two jobs at once: it means "the customer is still editing this order", and it also means "this row has been inserted and its real status has not been written yet". The cleanup job reads only the first meaning. It treats `'draft'` plus an old timestamp as positive evidence of abandonment, when the value is equally consistent with a row whose classifying write never happened.

That is the design fault, and it is real regardless of what else we find. A deletion predicate should confirm the thing it is deleting, not infer it from the absence of a marker that some other code path is responsible for adding.

## Open question: the dates do not reconcile

The obvious remediation does not fit the evidence, and this needs settling before the job runs again.

On 14 August the job's 90-day cutoff fell on 16 May. Every one of the 4,200 deleted rows therefore carried `status = 'draft'` and an `updated_at` earlier than 16 May. The change that introduced `pending_payment` merged on 11 August, three days before the run, so no row created or touched by that change could have had a timestamp old enough to match. The deleted rows were also `draft`, not `pending_payment`, which means the fix that first suggests itself, adding `AND status != 'pending_payment'` to the cleanup query, would not have saved a single one of them.

Three explanations are consistent with what we know, and they call for different fixes:

1. **The migration rewrote existing rows.** If the 11 August change collapsed a prior awaiting-transfer status into the new `'draft'` default, and did so with a write that did not update `updated_at`, a large population of long-dormant orders would have entered the cleanup query's range overnight. This is the only candidate under which 11 August is genuinely the trigger, and it is the leading hypothesis on the count alone: 4,200 rows appearing at once looks like a backfill, not like organic accumulation.
2. **The rows always matched and the job changed.** If bank-transfer orders have been sitting as `'draft'` all along, the cleanup job would have been deleting them every night for as long as both existed. That it did not means the job was recently enabled, recently retargeted, or previously failing. Under this explanation the 11 August change is a coincidence and the review finding, though still a genuine fault, is not the cause of this incident.
3. **`updated_at` is not maintained by the database.** If the column is set by application code rather than a trigger, any path that writes `status` without touching it can leave a row looking older than it is, and the two-step insert-then-update pattern becomes a durable trap rather than a momentary window.

Answering this requires the migration SQL from the 11 August change, the job's execution history and row counts for the preceding weeks, and the definition of how `updated_at` is maintained. Until we have that, we cannot say that any proposed change prevents recurrence.

## Contributing factors

**A deletion query with no upper bound.** The job had no ceiling on rows deleted and no comparison against the previous night's count. A jump to 4,200 in a job that normally removes abandoned drafts should have aborted the run rather than completed it.

**No dry-run and no per-row logging.** The job records a count and nothing else. This cost us twice: it prevented the change author from inspecting what the job would delete, and after the fact it left us unable to say which orders were affected without diffing the backup against production.

**No soft delete on the table.** Recovery required a restore from a point-in-time backup, which is why six orders lost an hour of writes. A soft delete would have made recovery a single update with no data loss at all.

**Review had no way to find the job.** The change was reviewed by one person, and nothing in the process surfaces the other consumers of a column whose semantics are being changed. The reviewer was not careless; they had no mechanism that would have shown them the cleanup query.

**Staging cannot reproduce age-dependent behaviour.** Staging holds no orders older than 30 days, so a job keyed on a 90-day threshold is untestable there by construction. Any interaction of this kind is invisible until it reaches production.

**Detection depended on a customer.** Nothing monitored deletion volume, order-count deltas, or the cleanup job's output. The 7 hours 16 minutes before the first report is the floor on how long any similar failure would go unseen, and it is a floor set by our customers' patience rather than by us.

## What went well

The backup was one hour old and restored cleanly, which held permanent loss to six orders out of 4,200. Once engineering had the cause, the job was disabled within five minutes and the restore was complete within three hours. The decision to leave the job disabled rather than patch and re-enable it was the right one and should hold.

## Action items

### Before the cleanup job is re-enabled

1. Recover the migration SQL from the 11 August change and determine whether it rewrote `status` on existing rows and whether it touched `updated_at`. This resolves the open question and gates everything else.
2. Pull the cleanup job's run history and per-run delete counts for the preceding 90 days, to establish whether the 4,200 was a step change or the first successful run in some time.
3. Document how `updated_at` is maintained on the orders table, in the database or in application code, and identify every write path that can set `status` without updating it.
4. Reconcile the 4,200 restored orders against payment records and confirm that no bank transfer was received against an order during the outage window. Identify the six orders with lost writes and contact those customers.

### Reduce blast radius

5. Add soft delete to the orders table and convert the cleanup job to set a deletion marker rather than issue `DELETE`. Hard removal becomes a separate, later, reviewable step.
6. Give the job a dry-run mode that writes the full set of candidate row identifiers to a log without deleting, and require a dry run in the deployment procedure for any change to its query.
7. Log every deleted identifier, not a count.
8. Add an abort threshold: if a run would affect more rows than some multiple of the trailing median, the job stops and alerts instead of proceeding.
9. Rewrite the predicate to confirm abandonment positively rather than infer it from `status = 'draft'`, for example by requiring the absence of any payment intent or transfer reference on the row. A row that cannot be positively classified should be left alone and reported.

### Detection and process

10. Alert on order-count deltas and on bulk deletions against the orders table, targeting detection in minutes rather than hours.
11. Give support a documented path for "customer reports missing data", so that a report of a vanished record escalates immediately rather than after 35 minutes.
12. Require that any change to the meaning, default, or permitted values of a status column enumerate the column's readers, including scheduled jobs and reports, and record that enumeration in the review.
13. Seed staging with data spanning the age ranges that scheduled jobs key on, or accept explicitly that time-threshold jobs are untested before production and compensate through the dry-run requirement in item 6.