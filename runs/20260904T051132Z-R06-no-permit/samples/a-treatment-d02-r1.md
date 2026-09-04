## Report skipped rows instead of silently truncating the contact import

### Why

Support received three reports this month of imports that reported success but landed fewer contacts than the customer's file contained. In each case the sheet had a blank row partway down, and `read_rows` treated the first empty cell in column A as end-of-data and stopped there. Everything below the gap was dropped without any signal, so the customer had no way to tell the import was incomplete. Separately, a single unparseable date aborted the entire run and surfaced a stack trace, discarding the rows that had already been read.

### What changed

`read_rows` now skips a row only when every cell in it is empty, and continues past it rather than breaking out of the loop. It also yields the sheet row index alongside the values so failures can be attributed to a specific line.

`import_file` wraps each `Contact.objects.create` in a `try`/`except ValueError` and collects `(line_no, message)` for the rows that fail, instead of letting the first bad row propagate. It returns an `ImportResult` carrying both the created count and the error list. The upload view passes both to `done.html`, so the results page tells the customer how many contacts were created and which rows were skipped and why.

### Behaviour change for callers

`read_rows` yields `(line_no, row)` where it previously yielded `row`, and `import_file` returns an `ImportResult` where it previously returned an `int`. Any other caller of either function needs updating; the view in this diff is the only one I changed.

### Tests

`test_blank_row_in_middle_does_not_truncate` reads a fixture with a gap partway down and asserts all 40 data rows come back. `test_bad_date_is_reported_not_raised` asserts that a sheet with one unreadable date creates the other 39 contacts and reports `(13, "could not read date '31/02/2026'")` rather than raising.

### Notes for review

Two things are not visible in this diff and are worth confirming before merge: the definition of and import for `ImportResult`, and the `done.html` block that renders `errors`. Without the template change the error list is passed to the page but never shown, which would leave the original silent-truncation complaint only half addressed.

The row number reported to the customer is the loop index `i`, which counts from the header at 0. For a sheet with one header row, `i == 13` is the fourteenth row of the file and appears as row 14 in the customer's spreadsheet application. If the intent is for the number in the error message to match what the customer sees in their own file, this needs a `+1` and the fixture expectation updated to match.