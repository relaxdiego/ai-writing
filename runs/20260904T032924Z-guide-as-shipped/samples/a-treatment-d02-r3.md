## Blank rows no longer truncate a contact import, and bad rows are reported instead of aborting

Support saw three reports this month of imports that reported success but landed fewer contacts than the file held. The cause was `read_rows` treating an empty first cell as end-of-sheet: a single blank row partway down a customer's spreadsheet silently discarded everything below it. Separately, one unreadable date anywhere in the file aborted the whole import and showed the customer a stack trace. Both failure modes now resolve the same way — the import processes the whole sheet and tells the customer which rows it could not use.

### What changed

`read_rows` no longer stops at the first row with an empty leading cell. It skips rows that are blank across every cell and continues to the end of the sheet, and it now yields `(line_no, row)` so failures can be attributed to a specific row.

`import_file` wraps each row's `Contact.objects.create` in a `try`, collects `ValueError` from `parse` into a list of `(line_no, message)` pairs, and returns an `ImportResult` carrying both the created count and those errors. A row that fails no longer stops the rows after it.

`views.upload` passes `result.created` and `result.errors` to `done.html`, so the results page lists what was skipped and why rather than reporting a clean success over a partial import.

### Behaviour change for callers

Two signatures changed, and any caller outside this diff needs updating:

- `read_rows(path)` yields `(line_no, row)` tuples, not bare rows.
- `import_file(path, account)` returns an `ImportResult`, not an `int`. Code doing arithmetic or truthiness checks on the return value will now be operating on the result object.

An import containing bad rows is now a success with errors attached rather than an exception. Anything upstream relying on an exception to signal "the import did not fully succeed" will no longer see one.

### Tests

`tests/test_spreadsheet.py` covers both reported failures: `blank-row-middle.xlsx` yields all 40 rows rather than stopping at the gap, and `bad-date.xlsx` imports 39 contacts and reports row 13 with `could not read date '31/02/2026'` instead of raising.

### Review notes

The line number in an error is the sheet index `i` from the enumeration loop, which starts at 1 for the first data row under the header. A customer looking at the same file in Excel sees that row numbered one higher, so the number we print will be off by one against what they can see on screen. Worth deciding here whether to convert at the boundary before this reaches the results page.

The diff also does not include the `ImportResult` definition or the `done.html` block that renders `errors`; both need to be in the branch for the results page to show anything.