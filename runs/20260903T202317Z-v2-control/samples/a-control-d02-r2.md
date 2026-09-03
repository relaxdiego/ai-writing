## Blank rows and bad dates no longer silently truncate contact imports

### Problem

Support received three reports this month of contact imports that reported success but created fewer contacts than the uploaded file contained.

Two separate causes:

1. **A blank row ended the import.** `read_rows` treated an empty first cell as end-of-data and stopped reading. Customers who left a spacer row partway down the sheet got a partial import with no indication anything was missing — the results page reported the truncated count as a success.
2. **One unreadable date aborted everything.** A single value `parse` couldn't handle raised out of the import loop, so the customer saw a stack trace and none of their contacts were created.

### Changes

**`read_rows`** now skips rows where every cell is blank rather than stopping at the first one, and yields the sheet row number alongside the values so failures can be attributed to a specific line.

**`import_file`** catches `ValueError` per row, records `(line_no, message)`, and continues. It returns an `ImportResult` with the created count and the list of errors instead of a bare integer.

**`upload`** passes both `created` and `errors` to the template, so the results page lists which rows were skipped and why.

### Behaviour change

`import_file` no longer returns an `int`. Any other caller of it needs updating to read `result.created`.

A file that previously aborted with a stack trace now succeeds partially and reports the bad rows. This is the intended behaviour — a customer with one malformed date gets the other 39 contacts plus a note about row 13 — but it does mean imports that used to fail loudly now complete.

### Tests

- `test_blank_row_in_middle_does_not_truncate` — a fixture with a spacer row partway down yields all 40 rows.
- `test_bad_date_is_reported_not_raised` — a fixture with one unparseable date creates 39 contacts and reports `(13, "could not read date '31/02/2026'")`.

---

Two things the diff doesn't show that I've assumed: `ImportResult` is defined elsewhere (or added in a hunk not included here), and `views.py` imports it or only touches the returned object's attributes. Worth confirming both are in the branch before this goes up.