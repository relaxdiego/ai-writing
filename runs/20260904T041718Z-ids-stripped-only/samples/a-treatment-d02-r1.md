## Report skipped rows instead of silently truncating the contact import

Support has had three reports this month of contact imports that reported success but produced fewer contacts than the file contained. In each case the sheet had a blank row partway down, and the importer treated it as end-of-data. Separately, one unreadable date anywhere in the file aborted the whole import and showed the customer a stack trace. Both failures shared a cause: the importer had no way to skip a row and keep going, so any surprise either ended the run early or ended it loudly.

### What changed

`read_rows` no longer stops at the first row with an empty first cell. It skips rows that are blank across every column and continues to the end of the sheet, so a gap in the middle of a file costs the rows in the gap and nothing after it. It now yields `(line_no, row)` rather than a bare row, which is what lets the caller name a specific row in a message to the customer.

`import_file` wraps each `Contact` creation in a `try`, collects `ValueError` from `parse` into a list of `(line_no, message)` pairs, and returns an `ImportResult` carrying both the created count and those errors. A file with one bad date now imports every other row.

`upload` passes `result.created` and `result.errors` to the template, and the results page lists each skipped row with the reason it was skipped.

### Behaviour change to be aware of

`import_file` used to return an `int` and now returns an `ImportResult`. Any other caller of it, or of `read_rows`, needs updating for both the new return type and the `(line_no, row)` tuple.

Only `ValueError` is caught. A row that fails for any other reason still aborts the import, which keeps genuine bugs visible rather than filing them as customer data problems.

### Tests

Two cases in `tests/test_spreadsheet.py`, one per report:

- `test_blank_row_in_middle_does_not_truncate` reads a 40-row fixture with an interior blank row and asserts all 40 rows come back.
- `test_bad_date_is_reported_not_raised` imports a 40-row fixture with one unparseable date and asserts 39 contacts created and a single error naming row 13 and the offending value.

### Not in this diff

The `ImportResult` definition and the `done.html` changes that render the error list are not part of the diff above; a reviewer will want both in front of them, since the customer-facing wording of the skipped-row list is the part support will be quoted back on.