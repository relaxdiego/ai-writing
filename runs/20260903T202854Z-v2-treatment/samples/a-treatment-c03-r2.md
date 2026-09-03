One test is failing, and it sits on the one place I did not carry the rename through: `src/admin/export_csv.py` still writes `"mobile"` in its CSV header row.

That file carries a comment saying the header names are the file format the finance team imports, and that changing them changes the file other people's spreadsheets read. So the row now reads `[user.id, user.name, user.phone, user.signed_up]`, following the model attribute, while `HEADERS` still reads `["id", "name", "mobile", "signed_up"]`. The consequence is `tests/test_export.py::test_csv_headers`, which asserts `'phone' in headers` and fails. Whether that test is wrong or the header really should change depends on something I can't see from the code: whether the finance import was updated alongside the database column. If it was, changing the string and the test is a two-line fix; if it wasn't, the header string is deliberately out of step with the field name and the test is asserting the wrong thing.

The rename is complete everywhere else, 23 occurrences in six files:

- `src/accounts/models.py`, `src/accounts/forms.py`, `src/accounts/serializers.py` — 11
- `src/notify/sms.py` — 3
- `tests/test_accounts.py`, `tests/test_notify.py` — 9

Those two test files pass, 20 tests. The full suite run showed the single `test_csv_headers` failure described above, and I have not re-run it since, because nothing has changed in that file.