# Import no longer stops at the first blank row or bad date

Support saw three reports this month of contact imports that reported success but landed fewer contacts than the file contained. Both failure modes came from `read_rows` and `import_file` treating any irregularity as the end of the work.

A blank row partway down a sheet ended the import. `read_rows` broke out of its loop when the first cell of a row was empty, so everything below that row was silently dropped and the customer was shown a success page with a plausible-looking count. Separately, a single unreadable date raised out of `import_file` and aborted the whole run, with the traceback reaching the customer.

| Sheet contains | Before | After |
| --- | --- | --- |
| A blank row at row 20 of 40 | 19 contacts, reported as success | 40 contacts |
| One unreadable date at row 13 | Stack trace, nothing imported | 39 contacts, row 13 listed as skipped |

## What changed

`read_rows` now skips a row only when every cell in it is blank, and continues past it rather than stopping. It also yields the row's line number alongside the values, so a failure can be attributed to a place in the file.

`import_file` catches `ValueError` from `parse` per row, records `(line_no, message)`, and carries on. It returns an `ImportResult` carrying the created count and the list of errors instead of a bare integer. The upload view passes both to the results page, so a customer who uploads a sheet with three bad dates gets the other rows imported and a list naming the three that were not.

## Tests

`tests/test_spreadsheet.py` covers both reported failures against fixtures: a sheet with a blank row in the middle now yields all 40 rows, and a sheet with one malformed date imports 39 contacts and reports the bad row rather than raising.

## For reviewers

Two things worth a look. `done.html` needs to render the new `errors` list; the template is not part of this diff, and without that change the errors are passed in and never shown. And the line numbers in the error tuples are the sheet index from `sheet.row_values`, which is offset from the row number the customer sees in Excel. Since these numbers now appear on the results page for people to act on, it is worth confirming the offset is what we want before this ships.