The rename is done everywhere except one string literal, and the full suite now has one failing test because of it.

I renamed 23 occurrences across the six files that grep found: `src/accounts/models.py`, `forms.py` and `serializers.py` (11), `src/notify/sms.py` (3), and `tests/test_accounts.py` and `tests/test_notify.py` (9). Those two test files pass, 20 tests.

The exception is `src/admin/export_csv.py:40`. The row builder there reads `user.phone`, so it matches the renamed model attribute, but `HEADERS` still lists `"mobile"`, and I left it that way on the strength of the comment directly above `row_for`: the column names are the file format the finance team imports, and changing them changes the file other people's spreadsheets read. The CSV that gets exported is therefore unchanged, same header row and same data.

That leaves `tests/test_export.py::test_csv_headers` failing, since it asserts `'phone' in headers`. Worth noting that this test already expected the new name before I touched anything, which pulls against the comment: either the header was meant to be renamed alongside the database column and the comment is stale, or the test is wrong and should still assert `'mobile'`. Renaming the header is outward-facing and breaks an import that people outside the repo depend on, so which of the two gets changed is your call, not mine.

One limit on the sweep: I grepped `src/` and `tests/` only, so migrations, templates, fixtures and docs were never searched for the old name.