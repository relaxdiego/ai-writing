**Don't truncate the contact import at a blank row, and report bad rows instead of aborting**

Support had three reports this month of contact imports that reported success but loaded fewer contacts than the customer's file held. The cause was `read_rows`: it treated an empty first cell as end-of-sheet and broke out of the loop, so a single blank row partway down a spreadsheet silently discarded everything below it. Separately, one unreadable date anywhere in the file raised out of `import_file` and the customer got a stack trace rather than their import.

`read_rows` now skips a row only when every cell is blank, and continues past it instead of stopping. It also yields the sheet's line number alongside the values, which is what makes per-row reporting possible downstream. `import_file` wraps each row's `Contact` creation and collects the `ValueError`s rather than letting the first one end the run; it returns an `ImportResult` carrying the created count and a list of `(line_no, message)` pairs. The upload view passes both into the template, so the results page lists the rows that were skipped and why, and the rows that parsed cleanly are still saved.

This changes the return type of `import_file` from an `int` to `ImportResult`. The view in this diff is the only caller updated; anything else calling it will need the same treatment.

Two tests cover the reported failures:

- `test_blank_row_in_middle_does_not_truncate` reads a fixture with a blank row partway down and asserts all 40 rows come back.
- `test_bad_date_is_reported_not_raised` imports a fixture with `31/02/2026` on line 13, and asserts the other 39 contacts are created and the bad line is reported rather than raised.