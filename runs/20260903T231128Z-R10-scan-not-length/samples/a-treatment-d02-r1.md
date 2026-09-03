## Report skipped rows instead of stopping the import

Three support reports this month came from imports that reported success but created fewer contacts than the file held. In each case a blank row partway down the sheet ended the import: `read_rows` treated an empty first cell as end-of-data and broke out of the loop, so every row below it was dropped without a word to the customer. Separately, one unreadable date anywhere in the file aborted the whole import and put a stack trace in front of the customer, discarding the rows that had parsed fine. Both failures now degrade to a per-row skip that the customer can see and act on.

### What changed

`read_rows` no longer stops at the first empty first cell. A row is skipped only when every cell in it is blank after stripping, and skipping continues past it rather than ending iteration, so a spacer row in the middle of a sheet costs one row instead of the remainder of the file. The generator now yields `(line_no, row)` so failures can be attributed to a position in the sheet.

`import_file` wraps each `Contact.objects.create` in a `try` for `ValueError`, records `(line_no, message)` on failure, and continues with the next row. It returns an `ImportResult` carrying `created` and `errors` in place of the bare count. `upload` passes both into `done.html`, which lists the rows that were skipped and why.

### For the reviewer

The line number reported to the customer is the sheet index used by the reader, which starts at 1 on the row after the header. A failure on the fourteenth row of the spreadsheet is therefore reported as 13, and the test asserting `(13, "could not read date '31/02/2026'")` encodes that. If the number in the results page is meant to be the row number the customer sees in their spreadsheet application, it needs `+1` at the point of display; I have left it matching the reader's index for now.

Two signatures changed shape. `read_rows` yields a tuple rather than a row, and `import_file` returns a result object rather than an `int`. `views.upload` is updated here; any other caller of either function, including management commands and anything in a background job, needs the same treatment, and a truthiness check on the old `created` return value would silently pass against the new object.

Only `ValueError` is caught. A row that fails parsing some other way, such as a `KeyError` from an unexpected column or a database integrity error on a duplicate, still aborts the import as before. That is deliberate for this change, since those cases suggest a problem with the file's structure or our schema rather than one bad cell, but it does mean the results page cannot claim to list every reason an import came up short.

### Tests

`test_blank_row_in_middle_does_not_truncate` reads a fixture with a spacer row and asserts all 40 data rows come back. `test_bad_date_is_reported_not_raised` imports a fixture with one malformed date and asserts 39 contacts are created and the failure is returned rather than raised. Neither the blank-row truncation nor the aborting parse error had a regression test before this change.