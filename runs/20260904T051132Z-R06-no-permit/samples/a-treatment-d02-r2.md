# Report skipped rows instead of silently truncating the contact import

## The problem

Support saw three reports this month of contact imports that reported success but landed fewer contacts than the customer's file contained. Two separate defects in `read_rows`/`import_file` produced that, and both are fixed here.

| Symptom | Cause | Now |
| --- | --- | --- |
| Import "succeeds" with a short count | A blank row partway down the sheet hit `if not row[0]: break`, ending the import at that point with no signal | Fully blank rows are skipped and iteration continues to the end of the sheet |
| Import aborts with a stack trace shown to the customer | A single unparseable value (for example a date of `31/02/2026`) raised out of `parse` and killed the whole run | The row is recorded as an error, the remaining rows still import |

## What changes

`read_rows` now yields `(line_no, row)` rather than a bare row, so a failure can be attributed to a position in the file, and it treats a row as blank only when every cell is empty after stripping, rather than testing the first column alone. `import_file` wraps each `Contact.objects.create` in a `try`, collects `(line_no, message)` for each `ValueError`, and returns an `ImportResult(created, errors)` instead of a bare integer. The upload view passes both fields to the results template so the customer sees which rows were skipped and why, rather than a count they have to reconcile against their own file by hand.

## Compatibility

The return type of `import_file` changed from `int` to `ImportResult`. Any caller outside `views.upload` needs updating; I only found the one, but it is worth a second pair of eyes during review.

## Tests

Two regression tests cover the reported failures directly: `test_blank_row_in_middle_does_not_truncate` asserts all 40 rows come back from a fixture with a gap in it, and `test_bad_date_is_reported_not_raised` asserts the run completes with 39 created and the offending row reported as `(13, "could not read date '31/02/2026'")`.

## Notes for review

Two things reviewers should confirm, since neither is settled by the diff. First, `done.html` needs to render the new `errors` list; that template change is not in this diff and the page will silently drop the errors until it is. Second, `line_no` is the `xlrd` sheet index, which is one less than the row number the customer sees in their spreadsheet application. The bad date in the fixture is on Excel row 14 and we report 13. If the number is going in front of a customer, it should probably be `i + 1`.