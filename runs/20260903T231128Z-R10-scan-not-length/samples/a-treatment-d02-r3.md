# Report skipped rows instead of silently stopping the import

## Why

Support saw three reports this month of contact imports that finished successfully but created fewer contacts than the customer's file contained. The cause was a blank row partway down the sheet: `read_rows` treated an empty first cell as the end of the data and broke out of the loop, so every row below the gap was dropped and nothing said so. A single unreadable date had the opposite failure mode, aborting the whole import with a stack trace on the customer's screen rather than skipping the one row it could not parse.

## What changed

- `read_rows` skips a row only when every cell is empty or whitespace, and continues past it instead of stopping. A row with any content at all still goes to `parse`, including one whose first cell is blank.
- `read_rows` now yields `(line_no, row)` so a failure can be attributed to a place in the file.
- `import_file` catches `ValueError` from `parse`, records it against the row number, and carries on with the rest of the sheet. It returns `ImportResult(created=..., errors=[(line_no, message), ...])` in place of the bare count.
- `upload` passes both `created` and `errors` to `done.html`, and the results page lists the rows that were skipped and why.

## Notes for reviewers

Two things worth a look. The first is the numbering the customer sees: `line_no` is the index `read_rows` uses against the sheet, which starts at 1 for the first data row because row 0 is the header. In the spreadsheet application the customer has open, that same row is row 2, so a reported "row 13" points them at row 14. If we want the error list to match what they can click on, the offset belongs in the template or in the message we build.

The second is the change to the `read_rows` signature. `import_file` is updated here because it is the caller I found, but anything else iterating `read_rows` will now unpack a tuple into what it expects to be a row of cells, and the failure will not be obvious at the call site.

Only `ValueError` is treated as a per-row problem; anything else `parse` raises still propagates and fails the import as before.

## Testing

`test_blank_row_in_middle_does_not_truncate` reads a fixture with a gap partway down and asserts all 40 rows come back. `test_bad_date_is_reported_not_raised` imports a sheet with one unparseable date and asserts the other 39 contacts are created and the bad row is reported as `(13, "could not read date '31/02/2026'")`.