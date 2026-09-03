# Postmortem: nightly cleanup deleted 4,200 live orders, 14 August 2026

The nightly draft-cleanup job deleted 4,200 live customer orders that were awaiting bank transfer, because a change merged three days earlier gave the `draft` status a second meaning and the job's query cannot tell the two apart. All 4,200 rows were restored from backup by 13:40 the same day. Six of them lost the changes made between the 01:00 backup and the 02:00 deletion, and those changes are gone permanently. Customers were without their orders for up to eleven hours and forty minutes, and we learned about it from one of them.

## Timeline

All times are on 14 August unless stated. Elapsed is measured from the start of the deletion at 02:00.

| Time | Event | Elapsed |
|---|---|---|
| 11 Aug | Change merged introducing the `pending_payment` status, reverting the column default to `'draft'`, and setting the new value from application code after insert | |
| 01:00 | Scheduled backup taken. This is the copy the restore was later made from | |
| 02:00 | Cleanup job starts | 0:00 |
| 02:04 | Job completes, logging a row count and nothing else | 0:04 |
| 09:20 | A customer telephones support to ask why their order has disappeared | 7:20 |
| 09:55 | Support escalates to engineering | 7:55 |
| 10:30 | Engineer confirms the deletion | 8:30 |
| 10:35 | Cleanup job disabled. It remains disabled | 8:35 |
| 13:40 | 4,200 rows restored from the 01:00 backup | 11:40 |

## What happened

The cleanup query encodes a definition: an order whose status is `draft` and whose `updated_at` is more than 90 days old is an abandoned cart. That definition was sound while `draft` had one meaning. The 11 August change gave it two. Because `pending_payment` is written by application code after the row is inserted rather than by the insert itself, `draft` became both the state an order genuinely abandoned in the cart sits in and the state every order passes through on its way to awaiting payment, including any order for which the follow-up write never landed. The cleanup job was never told about the second meaning, and no signal in the schema or the code connected the enum to the job that keys on it.

The second half of the failure is the timestamp. `updated_at` records when the row was last written, not when the customer last cared about it. An order waiting on a bank transfer is precisely an order nobody writes to: the customer has done their part, the money is moving through a bank, and neither side touches the record. Its `updated_at` freezes on the day the wait began, so the longer the transfer takes, the more closely the row resembles an abandoned cart by the only two signals the job consults. Bank transfers commonly run past 90 days before anyone gives up on them, which means the flow does not occasionally produce rows that match the deletion predicate; it produces them reliably.

We know the deleted population was 4,200 live orders only because the live table could be compared against the 01:00 backup. The job itself logs a single count per run and no identifiers, so it cannot tell us which of the rows it removed were legitimate abandoned drafts and which were not. That reconstruction had to be done by hand during the incident, and it is part of why confirmation took until 10:30.

## Why the change reached production

Three defences could have caught this and none of them was in a position to.

The review saw one reviewer and did not mention the cleanup job. This is not a lapse of attention so much as a missing input: nothing in the repository tells an author or a reviewer which batch jobs branch on `status`, so noticing the interaction required somebody to already hold that fact in their head.

Staging could not have surfaced it under any amount of testing. The environment holds no orders older than 30 days and the bug requires a row to be 90 days old. A time-dependent predicate is untestable in an environment with no aged data, and this one was.

The job itself has no safety margin. It has no dry-run mode, so nobody can ask what it would delete before it deletes it. It logs no identifiers, so nobody can tell afterwards what it took. There is no soft delete on the table, so the operation is immediately irreversible. There is no ceiling on the number of rows a single run may remove, so a query that suddenly matched roughly an order of magnitude more rows than usual proceeded exactly as if nothing had changed.

## Detection and recovery

The deletion finished at 02:04 and the first person to notice was a customer, seven hours and sixteen minutes later. The count the job logged at 02:04 contained the evidence, and nothing was watching it. A further thirty-five minutes passed in support before escalation, and another thirty-five before an engineer confirmed the cause, which is a reasonable pace for a ticket that arrived as a single confused customer rather than as an alert.

Recovery was fast once understood, but it was lossy in a way that was avoidable. Restoring from the 01:00 backup means undoing a 02:00 mistake by discarding an hour of legitimate writes. Six orders lost changes that way. With point-in-time recovery we would have replayed to 01:59 and lost nothing.

## Actions

Each of these needs an owner and a date assigned at the review meeting; they are listed roughly in order of how much protection they buy per unit of work.

- **Soft delete on the orders table.** Replace the `DELETE` with a `deleted_at` stamp, and move the physical removal to a separate purge that only touches rows soft-deleted more than 30 days ago. This converts the entire class of incident from data loss into a reversible mistake, and it is the single change that would have made 14 August a non-event.
- **Row ceiling with abort.** If a run selects more than a threshold derived from observed history, it aborts without deleting and raises an alert. A run of 4,200 would have stopped itself.
- **Alert on the count the job already logs.** The number existed at 02:04. Watching it costs almost nothing and would have cut eight and a half hours to minutes.
- **Dry-run mode and per-row logging.** The job should be able to emit the identifiers it would delete without deleting them, and every real run should write the identifiers it removed to durable storage.
- **Write the status in the insert.** Remove the default-then-update pattern so that a row's correct state does not depend on a second statement succeeding. This means touching the call sites the original change was written to avoid, and that cost should be paid.
- **Rewrite the predicate to use positive evidence of abandonment.** Exclude any order that has ever had a payment method or payment intent attached, and stop treating `updated_at` as a proxy for customer inactivity. A dedicated timestamp recording the last customer interaction would not freeze merely because the system stopped writing to the row.
- **Make consumers of `status` discoverable, and require two reviewers for changes to it.** A registry beside the enum listing the jobs and queries that branch on its values, plus a review checklist item asking the author to name them, and a second reviewer drawn from the owners of the batch jobs.
- **Seed staging with aged data spanning at least 120 days**, so that thresholds the production jobs depend on can actually be exercised there.
- **Enable point-in-time recovery** on this database so that recovery from a timed mistake does not require discarding the hour before it.

## Unresolved

Two things are not yet established and should be closed out before this postmortem is filed.

We have not confirmed the mechanism by which 4,200 rows were both `draft` and more than 90 days stale within three days of a merge that had not existed for 90 days. The likely candidates are a backfill or migration in the 11 August change that rewrote the column on existing awaiting-payment orders, or a pre-existing population of stuck rows that the change made newly eligible. The distinction matters: the first is a one-off blast radius, the second means the exposure was accumulating before the merge and may exist elsewhere. Reading the migration and checking the 01:00 backup for the distribution of `created_at` across the deleted rows should settle it.

We also do not know whether any affected customer re-placed an order during the eleven-hour window, which would leave a duplicate alongside the restored row. Support should be asked to check the tickets from that morning against the restored identifiers.