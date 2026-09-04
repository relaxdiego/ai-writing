# Report skipped rows instead of stopping the contact import

## Problem

Support saw three reports this month of contact imports that reported success but created fewer contacts than the customer's file contained. The cause was `read_rows` treating an empty first cell as end-of-sheet: a single blank row partway down a sheet silently truncated the import, and everything below it was discarded without a word to the customer. Separately, one unparseable date anywhere in the file aborted the entire import and surfaced a stack trace on the upload page, so a customer with one bad cell got no contacts and no explanation.

## What changed

A blank row is now skipped rather than treated as a terminator, and only rows where every cell is empty after stripping count as blank. `read_rows` yields the row index alongside the values so problems can be attributed to a specific row.

`import_file` no longer lets a `ValueError` from `parse` escape. Each failing row is collected as a `(line_no, message)` pair and the loop continues, so one unreadable cell costs one contact rather than the whole file. The return value changes from a bare count to `ImportResult(created=..., errors=...)`; `views.upload` passes both to the template, and the results page lists which rows were skipped and why.

This is a behaviour change for any other caller of `import_file` that expects an integer. `views.upload` is updated here; a reviewer familiar with the wider codebase should confirm there are no others.

## Tests

Two tests in `tests/test_spreadsheet.py` cover the reported failures directly:

- `test_blank_row_in_middle_does_not_truncate` reads a 40-row fixture with a blank row partway down and asserts all 40 rows come back.
- `test_bad_date_is_reported_not_raised` imports a fixture with one malformed date, asserting 39 contacts are created and the bad row is reported rather than raised.

## For the reviewer

Two things worth a close look. The row number reported to the customer is the loop index `i`, which is offset from the row number the customer sees in their spreadsheet application: the header occupies index 0, so index 13 in the test corresponds to row 14 in Excel. If the results page presents these as spreadsheet row numbers, they need `+ 1` before display.

Also, only `ValueError` is caught. Any other exception type raised by `parse` for malformed input will still abort the import, which is the behaviour this change set out to remove; worth confirming that `parse` raises nothing else on bad data.

The definition of `ImportResult` and the `done.html` changes that render the error list are not in this diff and will need to be reviewed alongside it.