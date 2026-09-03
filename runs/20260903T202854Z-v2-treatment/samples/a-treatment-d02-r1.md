# Report skipped rows instead of stopping the import at the first blank line

Support had three reports this month of contact imports that finished successfully but created fewer contacts than the uploaded file contained, plus imports that died with a stack trace on the customer's screen. Both come from the same habit in `read_rows` and `import_file`: the first sign of trouble ended the whole job.

`read_rows` stopped at the first row whose leading cell was empty, so a blank row partway down a sheet silently discarded everything below it. It now skips rows where every cell is blank and carries on, and it yields the sheet line number beside the values so later stages can report where a problem was. One consequence worth noting in review: a row with an empty first cell but data elsewhere is no longer treated as the end of the sheet, so it now reaches `parse` and will either import or be reported as an error rather than vanishing.

`import_file` previously let a `ValueError` from `parse` propagate, which aborted the run and threw away the rows already imported. It now catches that error per row, records the line number and the message, and continues to the end of the sheet. Errors from any other exception type still abort the import, which keeps genuine bugs visible rather than filing them as skipped rows.

The return value changes shape: `import_file` returns an `ImportResult` with `created` and `errors` instead of a bare count. `views.upload` is updated to unpack both and pass them to `done.html`, which now lists each skipped row and its reason. Any other caller still reading the old integer needs the same treatment, so that is the thing to check before merging.

Two tests cover the reported failures, each against a fixture:

- `blank-row-middle.xlsx` reads all 40 rows, where the old reader stopped short.
- `bad-date.xlsx` imports 39 contacts and reports `(13, "could not read date '31/02/2026'")` rather than raising.