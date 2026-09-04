## Blank rows and bad dates no longer silently shorten an import

Support saw three reports this month of contact imports that reported success but landed fewer contacts than the customer's file contained. The cause was `read_rows` treating an empty first cell as end-of-sheet: a blank row partway down a spreadsheet ended the import, and everything below it was dropped without a word to anyone. A separate failure came from the other direction — one unreadable date raised out of `import_file` and the customer got a stack trace instead of a result page, with no indication of which row was at fault.

### What changed

`read_rows` now skips a row only when every cell is blank, and continues rather than stopping, so a gap in the middle of a sheet no longer truncates the file. It also yields the sheet row number alongside the values, which is what makes per-row reporting possible downstream.

`import_file` catches `ValueError` from `parse` per row, records `(line_no, message)`, and keeps going. It returns an `ImportResult` carrying both the created count and the collected errors instead of a bare integer. The upload view passes both to `done.html`, so the results page lists the rows that were skipped and why.

### Behaviour change

A file that previously imported partially and reported success now imports fully. A file with one bad row previously failed entirely with a traceback; it now imports every other row and names the failure. `import_file`'s return type changed from `int` to `ImportResult`, so any other caller needs updating.

### Tests

`test_blank_row_in_middle_does_not_truncate` reads a fixture with a gap partway down and asserts all 40 rows come back. `test_bad_date_is_reported_not_raised` imports a sheet with `31/02/2026` on row 13 and asserts 39 contacts created plus one error naming that row and value.

### For review

Two things this diff depends on but doesn't show: the `ImportResult` definition, and the `done.html` change that renders the errors list. Worth confirming the template handles the empty-errors case cleanly, since that is the common path.