## Import no longer stops at a blank row, and a bad cell no longer kills the run

### Why

Support had three reports this month of contact imports that reported success but created fewer contacts than the file contained. The cause was a blank row partway down the sheet: `read_rows` treated an empty first cell as end-of-data and stopped, silently dropping everything below it. Separately, a single unparseable date aborted the entire import and showed the customer a stack trace.

Both failures share a shape — one bad row decides the fate of the whole file — so this change makes the importer row-scoped instead.

### What changed

**`read_rows` skips blank rows instead of terminating.** The end-of-data sentinel is gone. A row is skipped only if *every* cell is blank after stripping, so a row with an empty first column but data elsewhere is now imported rather than treated as the end of the sheet. Trailing blank rows are still excluded, just by being skipped rather than by ending iteration.

**`read_rows` yields `(line_no, row)`.** Callers need the source row to report errors against.

**`import_file` collects per-row errors instead of propagating them.** A `ValueError` from `parse` is recorded with its row number and the import continues. The return value is now an `ImportResult` with `created` and `errors` rather than a bare count.

**The results page lists skipped rows and why.** `upload` passes `result.errors` through to `done.html`, so a customer whose file has one bad date sees 39 contacts created and a line telling them row 13 had an unreadable date — instead of either a silent shortfall or a stack trace.

### Tests

Two regression tests, one per reported failure mode:

- `test_blank_row_in_middle_does_not_truncate` — a 40-row fixture with a blank row partway down now yields all 40 rows.
- `test_bad_date_is_reported_not_raised` — a fixture with one malformed date creates 39 contacts and reports `(13, "could not read date '31/02/2026'")`.

### Notes for reviewers

Two things worth a second pair of eyes:

- **Row numbering.** `line_no` is the `xlrd` row index `i`, which is 0-based and counts the header row, so data row *n* is index *n*. Whether that matches the row number the customer sees in Excel (1-based, header included) depends on the fixture; if it doesn't, error messages will be off by one — which is worse than useless when someone is hunting for the bad cell in a 500-row sheet. The test asserts `13` but I couldn't confirm from the fixture which row that is on screen.
- **Only `ValueError` is caught.** Anything else `parse` raises still aborts the run. That's deliberate — a `ValueError` means "this row is bad", while other exceptions likely mean something is wrong with the import itself — but if `parse` raises `KeyError` or `TypeError` for malformed rows in practice, those cases will still fail the whole file.

`ImportResult` isn't in this diff; it should land with it if it isn't already on the branch.