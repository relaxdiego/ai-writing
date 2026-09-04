# Import every row of an uploaded spreadsheet, and report the rows that fail

## Why

Support took three reports this month of contact imports that reported success but landed fewer contacts than the customer's file contained. The cause was `read_rows`, which treated an empty first cell as end-of-sheet and stopped there. A blank separator row partway down a sheet silently discarded everything below it, and nothing in the result told the customer that anything had been dropped.

The same import path had a second failure mode: `parse` raises `ValueError` on a value it cannot read, such as `31/02/2026`, and that exception propagated out of `import_file` and reached the customer as a stack trace. One bad cell threw away the other several hundred good rows.

## What changed

`read_rows` no longer terminates on a falsy first cell. A row is skipped only when every cell in it is blank after stripping, and the generator now yields `(row_index, row)` so a failure can be attributed to a place in the customer's file. `import_file` wraps each row's `Contact.objects.create` in a `try`, collects `(row_index, message)` for every `ValueError`, and returns an `ImportResult` carrying both the created count and the error list instead of a bare integer. The upload view unpacks that result and passes `created` and `errors` to `done.html`, which now lists the skipped rows and the reason for each.

| Input | Before | After |
| --- | --- | --- |
| Blank row partway down the sheet | Import stops there, reports success | Row skipped, remaining rows imported |
| Row with an empty first cell but data elsewhere | Import stops there, reports success | Row imported like any other |
| Cell that `parse` cannot read | `ValueError` escapes to the customer, nothing imported | Row skipped and reported, rest imported |

## Tests

`test_blank_row_in_middle_does_not_truncate` reads a 40-contact fixture with a blank row in the middle and asserts all 40 rows come back. `test_bad_date_is_reported_not_raised` imports a 40-row fixture containing one unreadable date and asserts 39 contacts created with a single reported error.

## Notes for reviewers

Two points need attention before this merges. `import_file` changes its return type from `int` to `ImportResult`, so any caller other than the upload view has to be updated in step; the diff covers only `views.upload`. The definition of `ImportResult` and the `done.html` changes that render the error list are not in the diff above and must land with it.

The number in each error tuple is the raw sheet index `i`, counting the header as row 0, so the failing date in the test fixture is reported as 13 while a spreadsheet application shows the customer row 14. Since this number is displayed to the customer, it is worth deciding here whether to add the offset in `read_rows` or at the template.