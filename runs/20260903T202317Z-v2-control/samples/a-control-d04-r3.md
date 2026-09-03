# Incident Postmortem: Nightly cleanup job deleted 4,200 live customer orders

**Date of incident:** 14 August
**Status:** Mitigated (cleanup job disabled); follow-up work open
**Author:** [author]
**Severity:** High — destructive, unrecoverable-by-design data loss affecting live customer records

---

## Summary

The nightly draft-order cleanup job deleted 4,200 live customer orders that were awaiting bank transfer. The job's deletion criteria (`status = 'draft'` and `updated_at` older than 90 days) had been correct for as long as `'draft'` meant "abandoned draft." A change merged on 11 August introducing a `pending_payment` status left `'draft'` as the database default and the resting state for orders awaiting payment, so long-running bank-transfer orders became indistinguishable from abandoned drafts. Bank transfers routinely take longer than 90 days, so a population of live orders aged past the deletion threshold.

The deletion was not detected by any system. It was detected 7 hours 16 minutes later by a customer who telephoned support to ask where their order had gone. Rows were restored from the 01:00 backup by 13:40; six orders permanently lost changes made between 01:00 and 02:00.

## Impact

- **4,200 live customer orders deleted**, unavailable to customers and to internal systems from 02:04 until 13:40 — **11 hours 36 minutes**.
- **6 orders permanently lost changes** made between 01:00 (backup) and 02:00 (deletion). This data is not recoverable.
- Unknown number of affected customers contacted support or attempted to interact with a missing order during the outage window; at least one did.
- **Customer-visible and trust-damaging**: the failure mode was "your order does not exist," with no error message and no explanation available to front-line support for 70 minutes.

## Timeline

All times on 14 August unless noted.

| Time | Event |
|---|---|
| 11 Aug | Change introducing `pending_payment` merged. `status` DB default set back to `'draft'`; payment code sets `pending_payment` in a separate write. Reviewed by one person; the cleanup job was not raised in review. |
| 02:00 | Nightly cleanup job starts. |
| 02:04 | Job completes. 4,200 live orders deleted. Job logs a count only. No alert fires. |
| 09:20 | A customer telephones support asking why their order has disappeared. (**7h16m after deletion**) |
| 09:55 | Support escalates to engineering. (**35m in support**) |
| 10:30 | Engineer confirms the rows were deleted by the cleanup job. (**8h26m after deletion**) |
| 10:35 | Cleanup job disabled. Bleeding stopped. |
| 13:40 | 4,200 rows restored from the 01:00 backup. (**11h36m after deletion**) |
| — | Cleanup job remains disabled. |

**Detection time:** 7h16m (external, by customer)
**Time to engineering confirmation:** 8h26m
**Time to mitigation:** 8h31m
**Time to recovery:** 11h36m

## Root cause

The cleanup job used `status = 'draft'` as a proxy for the business concept "abandoned by the customer." That proxy was valid only while `'draft'` had exactly one meaning. The `pending_payment` change gave `'draft'` a second meaning — "row written, subsequent status write not yet applied" — and made that the storage-level default for every order. The proxy silently stopped being valid, and nothing in the system encoded the dependency between the two.

The 90-day threshold was chosen against the lifecycle of an abandoned web draft. Bank-transfer orders have a lifecycle measured in months. Once the two lifecycles shared a status value, the threshold that was conservative for one became destructive for the other.

The specific mechanism deserves emphasis because it generalizes: **avoiding call-site changes by making the old value the default did not avoid the change — it moved the change from code, where reviewers and greps can see it, into data, where they cannot.** Every consumer of `status` was affected, but no consumer appeared in the diff.

## Contributing factors

**The change's blast radius was invisible to review.** A one-line default change altered the meaning of a column read by an unknown number of consumers. One reviewer, no inventory of who reads `status`, no prompt in the review process to enumerate consumers of a modified column. The cleanup job was never going to come up.

**Staging could not have caught this, structurally.** The bug requires data older than 90 days; staging holds nothing older than 30. This is not a gap in test coverage — it is a class of bug that the current pre-production environments cannot represent at all. Any time-threshold logic in this system is untested by construction.

**The job is built to be unauditable.** No dry-run mode, so the change in the job's selection set could not be observed before acting on it. No per-row logging, so after the fact we cannot say what was deleted without diffing against a backup. Only a count is logged.

**The job has no guardrails.** It deletes an unbounded set. A volume check would have caught this: the job already computes the count it needs, and 4,200 is presumably far outside its normal range. Nothing compared that number to anything.

**No soft delete on the table.** The destructive operation is immediate and irreversible at the application layer, so recovery required a backup restore, which forced an hour of unrelated writes to be rolled back — the six lost orders are a direct consequence of this design choice, not of the bug.

**Detection depended on a customer.** No monitoring covers order-count deltas, deletion volume, or orders vanishing from `pending_payment`. A quiet 4,200-row deletion at 02:00 produced no signal anywhere. If the affected customers had all been mid-transfer and not checking, this could have run for weeks.

**Support could not self-serve an answer.** 35 minutes elapsed between the customer call and escalation, which is reasonable for a novel report, but front-line support had no way to see that a record had been deleted rather than never existing.

## What went well

- Once escalated, engineering confirmed the cause in 35 minutes and disabled the job 5 minutes later.
- A usable hourly backup existed and the restore path worked; 4,194 of 4,200 orders were restored with no data loss.
- Support treated a single unusual customer report as a real signal rather than a user error.

## Open questions — resolve before anything else

1. **Did the job also delete rows on 12 and 13 August?** The change merged on 11 August and the job runs nightly. If the change was deployed before those runs, eligible rows would have been deleted then too, and the 14 August restore would not have recovered them — those deletions predate the backup that was restored. **This is the highest-priority item in this document.** Determine the deploy date, then diff order counts across 11–14 August against backups.
2. **What was the actual composition of the 4,200 rows?** Because the job logs no detail, we cannot state from logs whether the deleted rows were (a) genuinely awaiting bank transfer and correctly resting at `'draft'`, or (b) rows where the second write to `pending_payment` never landed — a separate latent bug. The restored rows are available; this can be answered by inspecting them, and should be.
3. **Are there other consumers of `status = 'draft'`** — reports, exports, reconciliation, dunning, analytics — that have been silently wrong since 11 August? The cleanup job is the consumer that failed loudly. Others may have failed quietly.
4. **Were the 6 orders with lost changes reconciled with those customers?** Confirm the changes were reconstructed or the customers contacted.

## Action items

Owners are unassigned; assign before closing this document.

**Immediate (block re-enabling the job)**

| # | Action | Owner |
|---|---|---|
| 1 | Answer open questions 1–3 above. Do not re-enable the cleanup job until 1 and 3 are resolved — the restored rows still match the current query and would be deleted again on the next run. | [ ] |
| 2 | Fix the selection criteria to name the condition explicitly rather than by proxy: exclude any order with a payment intent, and reconsider the 90-day threshold against real bank-transfer lifecycles. | [ ] |
| 3 | Add a volume guardrail: the job aborts and alerts if the candidate count exceeds a configured threshold or deviates sharply from its trailing average. | [ ] |

**Short term**

| # | Action | Owner |
|---|---|---|
| 4 | Add a dry-run mode that reports the full candidate set without deleting, and require a dry-run diff review before any change to the job or to `status` semantics. | [ ] |
| 5 | Log every deleted row's identifier and status, retained long enough to reconstruct any single run. | [ ] |
| 6 | Add soft delete to this table, with a retention period before hard delete, so recovery does not require rolling back an hour of unrelated writes. | [ ] |
| 7 | Alert on unexpected drops in live order count and on deletion volume from batch jobs generally. | [ ] |

**Longer term / systemic**

| # | Action | Owner |
|---|---|---|
| 8 | Remove the two-step write. `pending_payment` should be set in the same write that creates the row, so no order rests in a status that means something it isn't. Accept the call-site changes; they are the honest cost of the semantic change. | [ ] |
| 9 | Document the consumers of `status` and require that any change to its values or default enumerate and check them. Add this to the review checklist for enum and column-default changes. | [ ] |
| 10 | Give staging (or a dedicated test fixture) data spanning the age ranges the production thresholds care for, so time-dependent logic is testable at all. | [ ] |
| 11 | Audit other batch jobs for the same three properties: unbounded destructive scope, no dry-run, no per-row log. Fix them as a group rather than one incident at a time. | [ ] |
| 12 | Give support a way to see that a record was deleted, so "my order vanished" can be triaged in minutes rather than escalated blind. | [ ] |

## Lessons

The proximate bug was a status value. The reason it cost 4,200 orders was that a destructive, unbounded, unlogged, unrecoverable, unmonitored job sat at the end of the chain. Any one of a dry-run, a volume cap, a soft delete, or a count alert would have reduced this to a non-event. The status change was an ordinary mistake of the kind review will keep missing; the absence of every guardrail around a nightly `DELETE` is the finding worth acting on.

The second lesson is narrower and worth stating on its own: **changing a column's default to preserve old behaviour at call sites does not preserve old behaviour — it hides a semantic change from everyone whose job is to catch semantic changes.**

---

Want me to save this to a file in the repo, or adjust the tone/length for a particular audience (internal engineering vs. something customer- or exec-facing)?