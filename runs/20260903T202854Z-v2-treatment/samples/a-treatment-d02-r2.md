# Import every row, and report the ones that fail

Support has had three reports this month of contact imports that reported success but created fewer contacts than the file contained. Both causes were in the same loop. `read_rows` treated an empty first cell as end-of-sheet and stopped, so a blank row partway down a spreadsheet silently truncated the import at that point; separately, a single unparseable date raised out of `import_file` and gave the customer a stack trace instead of the rows that had already imported.

`read_rows` now skips a row only when every cell is blank, and continues rather than breaking, so nothing after a gap is lost. It also yields the sheet row number alongside the values, which is what makes per-row reporting possible downstream.

`import_file` wraps each `Contact.objects.create` so that a `ValueError` from `parse` is collected against its row number instead of aborting the run. The return value changes from a bare count to an `ImportResult` carrying `created` and `errors`, and `upload` passes both to the template, so the results page can tell the customer which rows were skipped and why. This is a breaking change for any other caller that treats the return of `import_file` as an integer; the only one in the tree is `upload`, which is updated here.

Two tests cover the reported failures directly: a fixture with a blank row in the middle yields all 40 rows, and a fixture with one bad date imports the other 39 and reports `(13, "could not read date '31/02/2026'")`.

Two pieces this change depends on are not in the diff and need to land with it: the `ImportResult` definition and its import into `spreadsheet.py`, and the `done.html` markup that renders the new `errors` list. Worth confirming before merge that the template degrades sensibly when `errors` is empty, since that is the common case.

Narrower than the fix but worth noting for a follow-up: only `ValueError` is caught, so a row that fails inside `Contact.objects.create` for a database reason still aborts the import. That seemed like the right line to hold for now, since a database error is not a per-row data problem the customer can fix by editing their spreadsheet.