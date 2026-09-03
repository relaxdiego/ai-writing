---
id: d04
register: document
name: Incident postmortem
---
Write an incident postmortem for the following incident.

On 14 August a nightly cleanup job deleted 4,200 live customer records. The job is meant to delete draft orders that were abandoned more than 90 days ago. It ran at 02:00 and finished at 02:04.

The job selects rows where `status = 'draft'` and `updated_at < now() - 90 days`. On 11 August a change was merged that introduced a new status value, `pending_payment`, for orders awaiting a bank transfer. To avoid touching many call sites the author set the database default for `status` back to `'draft'` and had the payment code set `pending_payment` after the row was written. Bank transfers commonly take longer than 90 days to be abandoned; orders that had been sitting for more than 90 days awaiting payment therefore matched the cleanup query.

Detection was by a customer, who telephoned support at 09:20 to ask why their order had disappeared. Support escalated at 09:55. An engineer confirmed the deletion at 10:30. The rows were restored from the 01:00 backup by 13:40, losing any changes made between 01:00 and 02:00, which affected 6 orders. The cleanup job was disabled at 10:35 and remains disabled.

The job has no dry-run mode and does not log what it deletes, only a count. There is no soft delete on this table. The change that introduced `pending_payment` was reviewed by one person and the cleanup job was not mentioned in the review. A staging environment exists but holds no orders older than 30 days, so the interaction could not have appeared there.
