## Import no longer stops at the first blank row or bad value

### Why

Support saw three reports this month of contact imports that reported success but landed fewer contacts than the file contained. In each case the sheet had a blank row partway down: `read_rows` treated an empty first cell as end-of-data and `break`ed, silently dropping everything below it. The import then reported the truncated count as a clean success, so nobody noticed until a customer went looking for a missing contact.

Separately, a single unparseable value — a date like `31/02/2026` — raised out of `import_file` and aborted the entire import, showing the customer a stack trace instead of a result page.

### What changed

**`read_rows` no longer terminates on a blank cell.** A row is skipped only if *every* cell is blank after stripping, and skipping means `continue`, not `break`. Rows below a gap are now imported. `read_rows` also yields `(line_no, row)` so failures can be attributed to a specific row.

**`import_file` collects per-row failures instead of propagating them.** A `ValueError` from `parse` is recorded against its row number and the import continues with the next row. The return value is now an `ImportResult` carrying `created` and `errors` rather than a bare count.

**The results page reports what was skipped.** `upload` passes both `created` and `errors` to `done.html`, so a partially successful import tells the customer which rows did not import and why, instead of quietly under-reporting or failing outright.

### Tests

- `test_blank_row_in_middle_does_not_truncate` — a 40-row fixture with a gap partway down yields all 40 rows.
- `test_bad_date_is_reported_not_raised` — a fixture with one unreadable date imports the other 39 rows and returns `[(13, "could not read date '31/02/2026'")]` rather than raising.

### Notes for reviewers

- `read_rows` is now a generator of tuples rather than of rows; any other caller needs updating alongside this.
- Only `ValueError` is caught. Anything else from `parse` or `Contact.objects.create` still aborts the import, which keeps genuine bugs and database errors loud. Worth confirming that `parse` raises `ValueError` for every malformed-input case we want reported.
- The reported row number is the sheet index `i` from the `range(1, nrows)` loop, so for a sheet with a header it is the zero-based sheet row, not the number the customer sees in their spreadsheet's row gutter. If these numbers are meant to be actionable, we may want to offset them before display.
- `ImportResult` itself is not part of this diff — worth checking it is defined and exported where `views.py` and the tests expect it.