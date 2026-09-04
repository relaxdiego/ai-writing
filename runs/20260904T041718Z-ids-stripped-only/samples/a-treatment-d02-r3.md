## Summary

Blank rows partway down an uploaded spreadsheet no longer truncate the import, and a single unparseable cell no longer aborts it. Support saw three reports this month of imports that reported success but created fewer contacts than the file contained; the cause was `read_rows` breaking out of the loop as soon as it hit a row with an empty first cell. A separate report had a customer shown a stack trace because one date read `31/02/2026`. Both now resolve to the same outcome: every row is attempted, and the rows that could not be imported are listed back to the customer with the reason.

## What changed

`read_rows` now skips a row only when every cell is blank, and it continues rather than stopping. It also yields the sheet row index alongside the values so failures can be attributed to a line the customer can find in their own file.

`import_file` collects `ValueError` from `parse` per row instead of letting it propagate, and returns an `ImportResult` carrying the created count and a list of `(line_no, message)` pairs. The upload view passes both to `done.html`, which lists the skipped rows underneath the success count.

## Behaviour change to be aware of

An import that previously died with a 500 now completes as a partial success. A customer who uploads 40 contacts with one bad date gets 39 contacts and one reported error rather than nothing at all, so the results page is now the only place that failure is surfaced — it needs to stay prominent enough that a partial import is not mistaken for a clean one.

The blank-row rule also widened slightly. A row with a stray value in some column other than the first used to end the import silently; it is now passed to `parse`, and will most likely appear as a reported error rather than being ignored. That seems right — a customer with junk below their data should be told about it — but it will make previously invisible mess visible on the first import after this ships.

## Testing

Two tests cover the reported cases directly: `test_blank_row_in_middle_does_not_truncate` asserts all 40 rows come back from a fixture with a gap in the middle, and `test_bad_date_is_reported_not_raised` asserts 39 contacts created plus the single error tuple for row 13. Both fixtures are built from the shape of the files support attached to the original reports.