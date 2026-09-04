# Report skipped rows instead of silently truncating the import

Contact imports stopped at the first blank row and reported success, so a customer whose sheet had a gap partway down got a "done" page and a partial import with no indication that anything was missing. Support saw three of these this month. Separately, one unparseable date aborted the entire run with a stack trace on the customer's screen. This change makes a bad row a reported row rather than a terminating one.

## What changed

`read_rows` no longer treats an empty first cell as end-of-data. It skips rows that are blank across every cell and keeps reading to the end of the sheet, and it now yields `(line_no, row)` so failures can be attributed to a position in the file.

`import_file` wraps each `Contact.objects.create` in a `try`/`except ValueError`, collecting `(line_no, message)` for the rows that fail and continuing with the rest. It returns an `ImportResult` carrying both the created count and the error list instead of a bare integer. The upload view passes both to `done.html`, so the results page lists what was skipped and why alongside the count of what succeeded.

## Compatibility

Two signatures changed and any caller outside this diff needs updating:

- `read_rows` yields a tuple, not a row.
- `import_file` returns `ImportResult`, not an `int`.

`done.html` needs a corresponding template change to render `errors`; the diff passes the list but does not show the template.

## Tests

`test_blank_row_in_middle_does_not_truncate` reads a 40-row fixture with a gap in it and asserts all 40 rows come back. `test_bad_date_is_reported_not_raised` imports a fixture with one unreadable date and asserts 39 contacts created plus a single error entry rather than a raised exception.

## For reviewers

Two things I could not settle from the diff alone. `ImportResult` is constructed in `import_file` and consumed in the view but is not defined in these files — confirm it is imported from wherever it lives and that the diff is not missing that hunk.

The reported line number is the sheet index `i` from `range(1, sheet.nrows)`, which is zero-based and skips the header, so the error asserted as row 13 in the test is the row a customer sees as 14 in their spreadsheet. Since these numbers now appear on a customer-facing page, they should probably be `i + 1`.