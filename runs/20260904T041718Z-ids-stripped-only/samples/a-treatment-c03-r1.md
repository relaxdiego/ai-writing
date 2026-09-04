The rename is done everywhere except the CSV export header, and that exception is now failing a test that needs your decision.

I renamed 23 occurrences: 11 across `src/accounts/models.py`, `forms.py` and `serializers.py`, 3 in `src/notify/sms.py`, and 9 across `tests/test_accounts.py` and `tests/test_notify.py`. Those two test modules pass, 20 tests.

The one I left is `src/admin/export_csv.py:40`, where `HEADERS` still reads `["id", "name", "mobile", "signed_up"]`. The comment above `row_for` says those column names are the file format the finance team imports, and that changing them changes the file other people's spreadsheets read. The row itself emits `user.phone`, so the data flows correctly; only the header label is stale, which is exactly the situation the comment describes as deliberate.

That leaves `tests/test_export.py::test_csv_headers` failing on `assert 'phone' in headers`, the only failure in the full suite. The two ways out point in opposite directions and neither is mine to pick, since both reach outside the repo:

- Rename the header to `phone`. The test passes and the finance team's import file changes shape.
- Leave the header as `mobile` and pin the test's expectation to it, with a note pointing at the comment. The export stays stable and the field/column mismatch becomes documented rather than accidental.

One gap in coverage worth knowing about: my search covered only `src/` and `tests/`, so any `mobile` in migrations, fixtures, templates, or docs is still there.