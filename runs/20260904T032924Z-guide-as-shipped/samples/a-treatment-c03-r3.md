The rename is done in six of the seven files, but the suite is not green and one decision is yours: `tests/test_export.py::test_csv_headers` fails, and fixing it means choosing between the test and the finance team's file format.

I renamed 23 occurrences across `src/accounts/models.py`, `forms.py`, `serializers.py`, `src/notify/sms.py`, `tests/test_accounts.py` and `tests/test_notify.py`. Those two test files pass, 20 tests.

`src/admin/export_csv.py` I left alone. Its `HEADERS` list still contains the literal string `"mobile"`, guarded by a comment saying the column names are the file format the finance team imports and that changing them changes what other people's spreadsheets read. The row builder in the same function already reads `user.phone`, so the code follows the renamed model attribute while the emitted header keeps the old label. That is the state the failing test catches: it asserts `'phone' in headers`.

Both resolutions are defensible and they are not equivalent, so I did not pick one:

- Keep `"mobile"` in `HEADERS` and update `test_csv_headers` to expect it. The database column rename is internal; the export stays byte-compatible with whatever the finance team imports.
- Change `HEADERS` to `"phone"` and leave the test as is. The export is then consistent with the model, and any downstream spreadsheet keyed on the `mobile` column breaks on the next import.

I lean toward the first: a column rename in your schema is not a reason to change a published file format, and the comment reads as a deliberate warning from someone who had that argument already. What makes me hesitate is that `test_csv_headers` asserts `'phone'`, which someone had to write; if that test was updated as part of the schema work, the intent may genuinely have been to change the format and notify finance separately.

Two caveats on what I verified. I ran the full suite once, saw the single failure, and after that only re-ran `tests/test_accounts.py` and `tests/test_notify.py` — I have not seen the whole suite pass. And I did not re-grep for `mobile` after editing, so the `HEADERS` string is the only remaining occurrence I know of rather than the only one that exists.