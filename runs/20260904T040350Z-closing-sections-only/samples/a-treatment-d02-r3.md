## Report skipped rows instead of truncating the import

### Problem

Support had three reports this month of imports that finished successfully but landed fewer contacts than the file held. `read_rows` broke out of its loop as soon as a row had an empty first cell, so a blank row partway down a sheet ended the import there and every row below it was dropped with nothing said about it. A second failure was noisier and just as lossy: a single unreadable date raised out of `import_file`, so the customer got a stack trace instead of a result page and lost the rows that had already parsed cleanly.

### What changed

`read_rows` now skips blank rows rather than treating one as the end of the data. The emptiness test also moved from "column A is falsy" to "every cell is empty once stripped", so a row that simply has no value in the first column is still imported. Each row is yielded with its sheet index so a failure can be attributed to a specific line.

`import_file` catches `ValueError` per row, records `(line_no, message)`, and carries on with the rest of the sheet. It returns an `ImportResult` carrying the created count alongside the errors, so a partial import is now a reportable outcome rather than an exception. The upload view passes both fields to `done.html`, which lists the rows that were skipped and why.

### Compatibility

Three interfaces changed together, and any caller outside this diff needs updating:

- `read_rows` yields `(line_no, row)` instead of `row`.
- `import_file` returns an `ImportResult` instead of an `int`.
- `done.html` now receives `errors` and must render it; a template that ignores the new key would put us back to reporting a clean success on a partial import.

### Tests

`test_blank_row_in_middle_does_not_truncate` reads a 40-row fixture with a gap partway down and asserts all 40 rows come through. `test_bad_date_is_reported_not_raised` imports a fixture with one malformed date and asserts the other 39 contacts are created and the failure is returned as `(13, "could not read date '31/02/2026'")` rather than raised.

### Note for review

The reported line number is the sheet index, where the header sits at index 0. Worth confirming it matches the row number the customer sees in their own spreadsheet before we put it on the results page, since a 1-based view with a header row would label that row 14 rather than 13.