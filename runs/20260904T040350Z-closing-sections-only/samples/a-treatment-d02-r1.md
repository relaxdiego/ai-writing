## Report skipped rows instead of silently truncating the import

### Why

Support saw three reports this month of contact imports that reported success but landed fewer contacts than the customer's file held. In each case a blank row partway down the sheet ended the import: `read_rows` treated an empty first cell as end-of-data and broke out of the loop, so every row below it was dropped without a word to anyone. Separately, a single unreadable date propagated a `ValueError` out of `import_file` and put a stack trace in front of the customer, discarding the rows that had already parsed cleanly.

Both failures share a cause worth naming, since the fix follows from it: the importer had no way to say "this row is bad" other than stopping. Blank rows stopped it quietly and bad values stopped it loudly, and neither told the customer which rows were affected.

### What changed

`read_rows` now skips a row when every cell is blank after stripping, rather than terminating the scan, and it yields the sheet line number alongside the values. `import_file` wraps each `Contact.objects.create` in a `try`, collects `(line_no, message)` for any `ValueError`, and returns an `ImportResult` carrying both the created count and the error list instead of a bare integer. The upload view passes both through to `done.html`.

| Input | Before | After |
| --- | --- | --- |
| Blank row at row 13 of 40 | 12 contacts, reported as success | 40 contacts |
| Unreadable date at row 13 | Stack trace, 0 contacts | 39 contacts, row 13 listed with its reason |

### Tests

`tests/test_spreadsheet.py` covers both reported failures against fixtures: `blank-row-middle.xlsx` asserts all 40 rows survive the scan, and `bad-date.xlsx` asserts 39 contacts are created and the offending row is reported as `(13, "could not read date '31/02/2026'")` rather than raised.

### Notes for review

Two things outside the Python hunks need a look before this merges. `done.html` has to render the new `errors` list, otherwise the failures stay invisible in a new way. And `read_rows` now yields a tuple rather than a row, so any caller besides `import_file` needs updating to match.