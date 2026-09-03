The rename is done everywhere except the CSV export, where it needs a decision from you before I finish it.

I renamed 23 occurrences across six files: `src/accounts/models.py`, `src/accounts/forms.py`, `src/accounts/serializers.py`, `src/notify/sms.py`, `tests/test_accounts.py` and `tests/test_notify.py`. Those two test modules pass, 20 tests green.

In `src/admin/export_csv.py` I stopped at the `HEADERS` list, which still reads `"mobile"`. The comment above `row_for` says those column names are the file format the finance team imports, so renaming the header changes a file other people's spreadsheets read rather than just our own code. The row body in that function reads `user.phone`, so the file currently pairs a `phone` attribute with a `mobile` column label.

That leaves `tests/test_export.py::test_csv_headers` failing on `assert 'phone' in headers`; it's the one failure in the full suite. Worth noting that this test already expected `phone` before I touched anything, since my grep for `mobile` never matched that file, which suggests someone intended the header to be renamed along with the database column. The comment in `export_csv.py` says the opposite. The two ways out:

- Change `HEADERS` to `"phone"`, which makes the test pass and changes the CSV the finance team imports, so they would need warning before the next export runs.
- Keep `"mobile"` as the header and change the test to assert `'mobile'`, which preserves the export format and leaves the internal field named `phone`.

I didn't pick one because only you know whether the finance team's import has been updated for the new column name.