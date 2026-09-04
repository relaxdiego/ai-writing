## Blank rows no longer truncate an import, and unreadable rows are reported instead of raised

Support saw three reports this month of imports that reported success but landed fewer contacts than the customer's file contained. In every case the sheet had a blank row partway down. `read_rows` treated an empty first cell as end-of-data and stopped there, so everything below the gap was dropped without any signal to the customer or to us. Separately, a single unparseable date aborted the entire import and put a stack trace in front of the customer, discarding the rows that had already been read.

Both failures came from the importer having no way to say "this row is bad" other than stopping. This change gives it one.

### What changed

`read_rows` now skips a row only when every cell is blank, and continues rather than breaking, so a gap in the middle of a sheet no longer hides the rows beneath it. It also yields the sheet row index alongside the values, which is what lets a failure be attributed to a specific row later on.

`import_file` wraps each `Contact.objects.create` in a `try`. A `ValueError` from `parse` is collected as `(line_no, message)` and the loop moves to the next row, so one bad date costs one contact instead of the whole file. The return value is now an `ImportResult` carrying both the created count and the collected errors.

The upload view passes both fields to `done.html`, and the results page lists the rows that were skipped and why.

### Callers

Two signatures changed and any other caller needs updating:

- `read_rows(path)` yields `(line_no, row)` rather than `row`.
- `import_file(path, account)` returns `ImportResult` rather than an `int`.

`views.upload` is the only caller in this repository and is updated here.

### Tests

`test_blank_row_in_middle_does_not_truncate` reads a fixture with a gap partway down and asserts all 40 rows come back, which fails on the old `break`. `test_bad_date_is_reported_not_raised` imports a sheet whose row 13 holds `31/02/2026` and asserts 39 contacts created with that one row reported, which previously raised out of the view.

### For review

The line number reported to the customer is the zero-based sheet index `i` from `enumerate` over `range(1, sheet.nrows)`, not the row number their spreadsheet application displays. With a header row present, the fixture's bad date sits on displayed row 14 but is reported as 13. If the results page shows this number to customers as a row reference, it should be offset before rendering, and `done.html` is worth a look on that point.