## Report skipped rows instead of silently ending the import

### Problem

Support saw three reports this month of contact imports that reported success but created fewer contacts than the file contained. `read_rows` treated an empty first cell as end-of-sheet and stopped there, so a blank row partway down a spreadsheet silently discarded everything below it, and the customer had no signal that anything was missing. Separately, one unreadable value anywhere in the file aborted the entire import: `parse` raised `ValueError`, nothing caught it, and the customer got a stack trace instead of their contacts.

### Changes

`read_rows` now skips a row only when every cell is blank, and continues rather than breaking, so a gap in the middle of a sheet no longer truncates the import. It yields the sheet row index alongside the values so failures can be attributed to a specific row.

`import_file` wraps each row's `Contact.objects.create` in a `try`/`except ValueError`, collecting `(line_no, message)` for the rows it could not parse and continuing with the rest. It returns an `ImportResult` carrying both the created count and the error list instead of a bare integer. The upload view passes both to `done.html`, which now lists the rows that were skipped and why.

A file with one bad date imports the other 39 contacts and reports the failure, where it previously imported nothing and showed an error page.

### Tests

Two cases in `tests/test_spreadsheet.py` cover the reported failures: a fixture with a blank row partway down yields all 40 rows, and a fixture with an unparseable date produces 39 contacts plus a single reported error rather than an exception.

### Notes for reviewers

The two signature changes are the parts worth a close look. `read_rows` now yields a tuple rather than a row, and `import_file` returns an object rather than an `int`, so any other caller of either function needs updating; `views.upload` is the only one changed here.

The reported line number is `i` from `range(1, sheet.nrows)`, which is the zero-based sheet index. For a sheet with a header in row 0, the error `(13, ...)` refers to what a customer opening the file in Excel sees as row 14. If the template renders this number to the customer, it should be offset before display.

Only `ValueError` is caught. Anything else `parse` or `create` raises still aborts the import, which keeps genuine bugs visible rather than logging them as per-row data problems.