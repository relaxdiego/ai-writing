The rename is complete except for one string literal, and the suite is red because of it.

`mobile` became `phone` in `src/accounts/models.py`, `forms.py` and `serializers.py` (11 occurrences), in `src/notify/sms.py` (3), and in `tests/test_accounts.py` and `tests/test_notify.py` (9). Those two test modules pass, 20 tests.

I left the header literal in `src/admin/export_csv.py:41` alone: `HEADERS` still reads `["id", "name", "mobile", "signed_up"]`. The comment above `row_for` says those names are the file format the finance team imports, and changing them changes the file other people's spreadsheets read, which is a different decision from renaming a database column. I did rename the attribute access in the same function to `user.phone`, since the model field has moved and the old name would now raise, so the export still emits the same bytes under the same header.

The cost of that choice is `tests/test_export.py::test_csv_headers`, which now expects `phone` among the headers and fails against the literal. Resolving it is a choice between two things I did not want to make on your behalf:

- Rename the header to `phone` as well, and tell finance the import file's third column has changed.
- Leave the header as the wire format and pin the test to it explicitly, so the export's column names stop tracking the model's field names.

Either is a one-line change. Which one is right depends on whether the finance importer keys on the header text or on column position.