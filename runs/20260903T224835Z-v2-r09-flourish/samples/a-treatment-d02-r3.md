**Title:** Report skipped rows instead of silently truncating the contact import

An import that finishes "successfully" with fewer contacts than the customer uploaded is worse than one that fails, and we've had three support reports of exactly that this month. This change makes both known causes visible on the results page instead of swallowing them.

The two failures behaved differently but had the same effect on the customer:

- A blank row partway down the sheet ended the import. `read_rows` treated an empty first cell as the end of the data and `break`, so every row below the gap was dropped without a word.
- A single unreadable date aborted the whole run. `parse` raised `ValueError`, nothing caught it, and the customer got a stack trace instead of their contacts.

`read_rows` now skips a row only when every cell is blank after stripping, and continues rather than breaking, so a gap in the middle of the sheet costs one row instead of the remainder of the file. It also yields `(line_no, row)`, since a row number the customer can find in their own spreadsheet is the only useful way to report a skip. `import_file` wraps each `Contact.objects.create` in a try/except for `ValueError`, collects `(line_no, message)` for each failure, and returns an `ImportResult` carrying both the created count and the errors. Good rows in a file with one bad date are now imported.

The signature change to `read_rows` and the new return type of `import_file` affect their callers; `views.upload` is the only one, and it now passes `created` and `errors` separately to `done.html`.

One thing to check in review: this diff does not touch `done.html`, so the errors need corresponding markup in the template before the new list is visible to anyone.

Two tests cover the reported cases: a fixture with a blank row in the middle yields all 40 rows, and a fixture with an unreadable date imports 39 contacts and reports row 13 with the offending value.