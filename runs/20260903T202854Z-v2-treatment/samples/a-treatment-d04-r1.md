# Postmortem: nightly cleanup job deleted 4,200 live orders

**Status:** cleanup job disabled since 14 August 10:35. It should stay disabled until action item 1 is closed, because we cannot currently say which rows it would select.

## Summary

Between 02:00 and 02:04 on 14 August the nightly cleanup job deleted 4,200 live customer orders. The job is meant to remove draft orders abandoned for more than 90 days, and it did exactly what it was written to do: it deleted every row with `status = 'draft'` and `updated_at` older than 90 days. A change merged on 11 August had made `draft` the resting state of orders that were alive and waiting on a bank transfer, so the predicate that once meant "abandoned" now also matched orders that were not abandoned at all.

Nothing in our systems noticed. Detection came from a customer, seven hours and twenty minutes after the deletion, and confirmation took another seventy minutes after that. All 4,200 rows were restored from the 01:00 backup by 13:40. Six orders lost the changes made to them between 01:00 and 02:00; those changes are gone and cannot be reconstructed from any source we hold.

## Timeline

All times are 14 August, local.

| Time | Elapsed | Event |
|---|---|---|
| 02:00 | — | Cleanup job starts |
| 02:04 | +4m | Job completes, having deleted 4,200 rows; logs a count only |
| 09:20 | +7h20m | Customer telephones support asking why their order has disappeared |
| 09:55 | +7h55m | Support escalates to engineering |
| 10:30 | +8h30m | Engineer confirms the rows were deleted by the cleanup job |
| 10:35 | +8h35m | Cleanup job disabled |
| 13:40 | +11h40m | All 4,200 rows restored from the 01:00 backup |

## What happened

The 11 August change introduced a new status value, `pending_payment`, for orders awaiting a bank transfer. Rather than update every call site that writes an order, the author left the database default for `status` as `'draft'` and had the payment code issue a second write to set `pending_payment` after the row already existed. This split the meaning of a single column across two writes and two code paths. A row sitting in `draft` no longer told you whether the customer had walked away or whether the second write had simply not happened yet, had failed, or had been bypassed by a write path that did not run through the payment code.

The cleanup job was written against the older, single meaning. Its query is a business rule ("this order is abandoned") expressed as a storage fact ("this row says draft"), and the change quietly broke the correspondence between the two. Bank transfers routinely sit unresolved for longer than 90 days, so a population of live orders was both `draft` and old, which is the exact shape the job hunts for.

## What we have not established

The account above is incomplete on one point that matters for reopening the job. A default-value change applies to new inserts and does not rewrite existing rows, and the merge was only three days before the incident, so newly created orders could not have aged past 90 days in that window. For 4,200 rows to be both `draft` and older than 90 days on the morning of the 14th, one of the following must be true, and we do not yet know which:

- the 11 August migration also updated existing rows, backfilling them to the `'draft'` default;
- bank-transfer orders were already resting in `draft` before the change, and something else in the merge made the cleanup job newly eligible to see them or newly able to run to completion;
- the payment code's second write has been failing for a subset of orders for some time, and the change altered how many of them there were.

Until we can point at the specific mechanism, we cannot claim the fix. Reconstructing it from the migration, the deployment record and the restored rows' `created_at` distribution is the first action item.

## Contributing factors

Beyond the immediate cause, four things turned a bad query into four hours of customer-facing data loss:

- **No dry-run and no per-row logging.** The job records a count and nothing else. Confirming what had been deleted required inference rather than reading a log, which is most of the gap between 09:55 and 10:30.
- **No soft delete on the table.** With a `deleted_at` column the recovery would have been an `UPDATE` taking seconds and losing nothing. Instead it was a restore from an hour-old backup, which is why six orders lost an hour of edits.
- **The review had no way to see the blast radius.** One reviewer looked at a change to how `status` is written, with no prompt to ask who reads `status`. The cleanup job was never mentioned.
- **Staging cannot reproduce age-dependent behaviour.** It holds no orders older than 30 days, so no test of a 90-day predicate can fail there. Any job whose correctness depends on data age is effectively untested before production.

## Action items

1. Establish the exact mechanism by which 4,200 pre-existing rows came to satisfy the cleanup predicate, using the migration SQL and the `created_at` distribution of the restored rows. Blocks everything below.
2. Stop deriving "abandoned" from `status`. Introduce an explicit column or state machine so that a row awaiting payment cannot be represented as a draft, and remove the two-step write by having call sites set the status at insert.
3. Add soft delete to the orders table and convert the cleanup job to set `deleted_at`, with a separate, much later hard-delete pass.
4. Give the job a dry-run mode that is the default in every environment except the scheduled production run, and have it log the primary key of every row it removes.
5. Add a guardrail on the job: if the candidate set exceeds a threshold, or exceeds the trailing median by some multiple, abort and alert rather than proceed.
6. Alert on bulk deletion volume per table, independent of the job that caused it. Seven hours of silence is the largest single contributor to the impact here.
7. Seed staging with orders spanning at least a year, or give the cleanup tests a way to control the clock, so age-dependent logic is exercisable before it reaches production.
8. Add the consumers of `status` to a review checklist for changes to order state, so a reviewer is asked the question that was not asked on 11 August.

Owners and dates for items 2 through 8 need assigning; item 1 is with the engineer who handled the incident.