# Incident Postmortem: Cleanup job deleted 4,200 live customer records

**Date of incident:** 14 August
**Status:** Mitigated (cleanup job disabled); root cause not fully confirmed — see Open Questions
**Severity:** High — irreversible deletion of live customer data, customer-visible, detected externally

---

## Summary

The nightly draft-order cleanup job deleted 4,200 live customer records. The job is intended to delete abandoned draft orders older than 90 days. It selects on `status = 'draft'` AND `updated_at < now() - 90 days`. On 11 August a change introduced a new status, `pending_payment`, for orders awaiting bank transfer; the change kept `'draft'` as the database column default and relied on payment code to set `pending_payment` after the row was written. Bank-transfer orders routinely sit for more than 90 days, so orders in this flow fell inside the cleanup job's age window.

The deletion was not detected by monitoring. A customer telephoned support seven hours later to ask why their order had disappeared. Rows were restored from the 01:00 backup, losing all changes made between 01:00 and 02:00; 6 orders were affected by that gap.

## Impact

- **4,200 live customer records deleted.** Composition of these records is not yet established (see Open Questions).
- **6 orders lost changes** made between 01:00 and 02:00 and not recovered by the restore. These have not yet been reconciled.
- **Customer-visible:** at least one customer found their order missing and contacted support. The number of customers who noticed but did not call is unknown.
- **Data unavailable for approximately 11h40m** (02:00–13:40) for the deleted rows.
- **Cleanup job disabled since 10:35 on 14 August** and still disabled, so abandoned drafts are now accumulating.

## Timeline

All times on 14 August unless noted. Timezone as recorded in the source report.

| Time | Event |
|---|---|
| 11 Aug | Change introducing `pending_payment` merged. Reviewed by one person; cleanup job not raised in review. |
| 02:00 | Nightly cleanup job starts. |
| 02:04 | Job completes. 4,200 rows deleted. Job logs a count only. No alert fires. |
| 09:20 | Customer telephones support asking why their order disappeared. **Time to detect: 7h16m.** |
| 09:55 | Support escalates to engineering. **35m in support queue.** |
| 10:30 | Engineer confirms the deletion. |
| 10:35 | Cleanup job disabled. **Time to mitigate: 8h31m.** |
| 13:40 | Rows restored from the 01:00 backup. Changes made 01:00–02:00 lost for 6 orders. **Time to resolve: 11h40m.** |

## Root cause and contributing factors

**Primary cause.** The cleanup job encoded the assumption that `status = 'draft'` means "abandoned." The 11 August change made `'draft'` also mean "newly created, status not yet assigned," but the cleanup job — an unlisted consumer of the `status` column — was never updated. The predicate is a deny-by-omission design: any new status that leaves rows sitting in `'draft'` silently becomes deletable.

**Contributing factors.** None of these caused the incident alone; each one, if absent, would have reduced its severity or duration.

1. **Status set by database default plus a follow-up application write.** Choosing the column default over touching call sites meant correctness depended on a second write landing. The decision was made to reduce diff size; the trade-off was not surfaced in review.
2. **Review did not enumerate consumers of `status`.** One reviewer, and no mechanism prompting either party to ask "what else reads this column?" The cleanup job is exactly the kind of consumer that no call-site search would surface as urgent.
3. **No dry-run mode.** There was no way to see what the job would delete before it deleted it, either during the change or during triage.
4. **No per-row logging.** The job logs a count only. We still cannot say which records were deleted without diffing backups — this directly slowed triage and still limits our ability to answer customers.
5. **No soft delete on the table.** Deletion was immediately irreversible in place, forcing a backup restore and making the 01:00–02:00 data loss unavoidable.
6. **No blast-radius guard.** The job deleted 4,200 rows without an abort threshold. A sane nightly volume would have been far lower.
7. **No alerting on deletion volume.** Detection depended entirely on a customer noticing and calling.
8. **Staging holds no orders older than 30 days.** Any bug whose trigger is a 90-day age window is structurally undetectable in staging. This is a gap in the environment, not an oversight by the change author — the interaction could not have appeared there.

## Open questions

These must be answered before the cleanup job is re-enabled. The postmortem's causal account does not yet fully close.

1. **How were these rows still `'draft'` at 02:00?** A bank-transfer order that has been through the payment code carries `status = 'pending_payment'` and does not match the cleanup predicate. For 4,200 rows to have matched, they must have been `'draft'` at deletion time. Candidate explanations, none confirmed: (a) the payment code's follow-up write failed or never ran for these rows, leaving them at the default indefinitely; (b) the payment path is reached later in the order lifecycle than assumed, so rows sit as `'draft'` for a long period; (c) the deleted rows were not `pending_payment` orders at all, and the link to the 11 August change is inferred rather than established. Which of these is true changes the fix.
2. **Why 14 August and not 12 or 13 August?** The job runs nightly and the change merged on 11 August. The job's deleted-row counts for the nights of 12 and 13 August are in the logs and should be checked immediately. **If rows were also deleted on those nights, they are absent from the 01:00 14 August backup and are still missing today** — the restore would not have recovered them.
3. **What was the composition of the 4,200?** Legitimate abandoned drafts and wrongly-deleted live orders are currently indistinguishable in our records.
4. **What changed for the 6 orders between 01:00 and 02:00?** Not yet reconstructed; may be recoverable from application or payment-provider logs.

## What went well

- Support escalated a single unusual customer report rather than treating it as an isolated account issue.
- Once escalated, engineering confirmed the cause and stopped the bleeding within 40 minutes.
- A recent backup existed and the restore path worked, limiting permanent loss to 6 orders.

## What went poorly

- Detection was external and took over seven hours. We had no independent signal that 4,200 records had vanished.
- We could not determine what had been deleted from our own logs.
- The job's design offered no safe way to inspect, limit, or reverse its work.

## Action items

The cleanup job stays disabled until items 1–5 are complete.

| # | Action | Priority |
|---|---|---|
| 1 | Answer Open Questions 1 and 2. Check job counts for 12 and 13 August; if rows were deleted then, treat recovery of those rows as a new incident — they are not covered by the 14 August restore. | P0 |
| 2 | Rewrite the cleanup predicate as an explicit allow-list of statuses safe to delete, so any future status fails closed rather than becoming deletable by omission. | P0 |
| 3 | Add soft delete to the orders table; convert the cleanup job to soft-delete with a separate, delayed hard-delete pass. | P0 |
| 4 | Add a dry-run mode and per-row logging of deleted primary keys and statuses. | P0 |
| 5 | Add a row-count abort threshold, tuned to observed normal nightly volume, that fails the job rather than proceeding. | P0 |
| 6 | Reconcile the 6 orders with lost 01:00–02:00 changes; contact affected customers. | P0 |
| 7 | Alert on bulk deletion volume across all destructive jobs, not just this one. | P1 |
| 8 | Inventory every consumer of `orders.status`, including jobs, reports and queries outside the application codebase. Publish the list next to the column definition. | P1 |
| 9 | Add a review checklist item for changes to enum or state values: enumerate readers, not just writers. Require a second reviewer for state-model changes. | P1 |
| 10 | Seed staging with aged data spanning the retention windows the system enforces (>90 days for orders), so time-dependent logic is testable. | P1 |
| 11 | Reconsider assigning status via database default plus a follow-up write. Prefer explicit status at insert, even at the cost of touching call sites. | P2 |

Owners and due dates to be assigned at the review meeting.

---

**Note on blame.** The change author made a reasonable local trade-off — reduce diff size, avoid touching many call sites — with no way to see the cleanup job from where they were standing. The job was invisible to call-site search, invisible in review, and untestable in staging. The failure is in those three gaps, not in the decision.

---

I've kept this to the facts given and flagged what doesn't reconcile rather than smoothing it over. Open Question 2 in particular is worth checking today — if the job also ran destructively on 12 or 13 August, there is unrecovered data loss right now. Want me to save this to a file in the repo?