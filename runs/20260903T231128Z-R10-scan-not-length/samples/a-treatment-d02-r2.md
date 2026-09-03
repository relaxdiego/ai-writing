## Blank rows and bad dates no longer silence a contact import

Support has had three reports this month of an import that reported success but created fewer contacts than the file contained. The cause was `read_rows` treating an empty first cell as end-of-sheet: a blank row partway down a customer's spreadsheet ended the loop, and everything below it was dropped without a warning. Separately, a single unparseable date raised out of `import_file` and put a stack trace in front of the customer, losing the rows that had already been read.

### What changed

`read_rows` now skips a row only when every cell in it is blank, and it continues past that row rather than stopping. It also yields the sheet row index alongside the values so a problem can be attributed to a specific row.

`import_file` catches `ValueError` from `parse` per row, records the row and the message, and carries on with the rest of the sheet. It returns an `ImportResult` carrying the created count and the list of errors instead of a bare integer, and `upload` passes both to `done.html`, so the results page lists which rows were skipped and why.

### Behaviour change for callers

`import_file` no longer returns an `int`. Any other caller reading the return value directly needs `result.created`. This is the only signature change in the diff.

| Input | Before | After |
| --- | --- | --- |
| Blank row at sheet row 20 of 40 | 19 contacts, reported as success | 40 contacts |
| One unreadable date | Stack trace, no import | 39 contacts, one error listed |
| Trailing blank rows | Loop stops, no error | Skipped, no error |

### Tests

`test_blank_row_in_middle_does_not_truncate` imports a fixture with a blank row partway down and asserts all 40 rows survive. `test_bad_date_is_reported_not_raised` asserts the good rows are created and the failure is returned as `(13, "could not read date '31/02/2026'")` rather than raised.

### Notes for reviewers

The row number in the error tuple is the raw sheet index, which is one less than the row number the customer sees in their spreadsheet application, since the header occupies index 0. The test expecting `13` is consistent with the code, but if that number is rendered on the results page the customer will be pointed at the wrong row. Worth deciding whether to add the offset here or in the template.

The diff does not include the definition of `ImportResult` or its import in `views.py`; I have assumed both exist elsewhere in the branch.