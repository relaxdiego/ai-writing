# Report skipped rows instead of stopping the import

## Why

Support saw three reports this month of contact imports that finished successfully but landed fewer contacts than the customer's file contained. In each case a blank row partway down the sheet ended the import silently: `read_rows` treated an empty first cell as end-of-data and broke out of the loop, so every row below the gap was dropped without any indication that it had happened. Separately, one unreadable date anywhere in the file aborted the entire import and showed the customer a stack trace, losing the rows that had already parsed cleanly.

## What changed

`read_rows` no longer stops at the first row with an empty first cell. A row is skipped only when every cell in it is blank after stripping whitespace, and the reader continues to the end of the sheet either way. It now yields the sheet row index alongside the values so failures can be attributed to a row.

`import_file` wraps each row in a `try` and collects `ValueError` from `parse` into an errors list rather than letting it propagate. Instead of a bare count it returns an `ImportResult` carrying `created` and `errors`, and `upload` passes both into the template, so the results page lists the rows that were skipped and why.

## Behaviour change

| Input | Before | After |
| --- | --- | --- |
| Blank row partway down | Import stops there, reports success | Row skipped, rest of file imported |
| Row with an unreadable date | Whole import aborts with a stack trace | Row skipped and reported, other rows imported |
| Clean file | Count of created contacts | Same count, empty error list |

An import that hits bad rows is now a partial success rather than a failure, so a customer who previously saw an error page will see a completed import with a list of skipped rows. `done.html` needs to handle a non-empty `errors` list.

## Tests

`tests/test_spreadsheet.py` covers both reported failures: a fixture with a blank row in the middle reads all 40 rows, and a fixture with one unparseable date creates 39 contacts and returns the failing row and its message rather than raising.

## Notes for reviewers

Two things worth a second opinion. The row number in an error is the index from `sheet.row_values`, which counts from the first data row rather than from the top of the sheet, so a customer comparing it against the row numbers in their own spreadsheet will be off by one for the header. If the results page shows these numbers to customers, they should probably be `i + 1`.

Only `ValueError` is caught. Anything else `parse` raises still aborts the import, which preserves the current behaviour for genuinely unexpected failures but means a `KeyError` on a missing column still costs the customer the whole file.