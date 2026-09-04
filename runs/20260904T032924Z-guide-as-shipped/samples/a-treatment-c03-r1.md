The rename is done in the application code and tests, but the suite is currently red: `tests/test_export.py::test_csv_headers` fails, and fixing it means changing a file format that people outside the codebase consume. I stopped there rather than make that call myself.

Renamed 23 occurrences across the files that grep turned up:

- `src/accounts/models.py`, `src/accounts/forms.py`, `src/accounts/serializers.py` — 11
- `src/notify/sms.py` — 3
- `tests/test_accounts.py`, `tests/test_notify.py` — 9

Those two test files pass, 20 tests.

The holdout is `src/admin/export_csv.py`. The attribute read in `row_for` now uses `user.phone`, but the `HEADERS` list still emits `"mobile"` as the CSV column name, and there is a comment on the function saying those column names are the format the finance team imports and that changing them changes what other people's spreadsheets read. A field rename in your database does not by itself mean the exported file should change its header, so I left the string alone. `test_csv_headers` asserts `'phone' in headers` and fails against it.

That leaves a real decision for you. If the export is meant to track the internal field name, change `HEADERS` to `"phone"` and the test goes green with no further work, but the next import on the finance side sees a column it does not recognise. If the export is a stable contract, `HEADERS` stays as it is and `test_export.py` is the thing that is wrong: it should assert `'mobile'`, pinning the header to the file format rather than to the model. I lean toward the second, because the comment reads as someone having already thought about this, but I do not know whether the finance import has been updated alongside the database column.