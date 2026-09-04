The rename is done in the application code and tests, but I stopped at one line in `src/admin/export_csv.py` and the full suite has one failure because of it. That line needs your decision.

`HEADERS` at `src/admin/export_csv.py:40` still reads `["id", "name", "mobile", "signed_up"]`. The comment directly above `row_for` says these column names are the file format the finance team imports, and that changing them changes the file other people's spreadsheets read. That is an external contract rather than an internal field name, so I left it alone rather than break someone's import silently. Note that the body of `row_for` already reads `user.phone`, so the header string is the only thing in that file still saying "mobile" — the code and the header now disagree.

That disagreement is what `tests/test_export.py::test_csv_headers` catches: it asserts `'phone' in headers` and fails. That test file never contained the string "mobile", so it wasn't in my grep and I didn't edit it; someone appears to have already begun this rename on the export side and stopped partway. Whether the test is right depends on the same call — if the CSV is meant to change, update `HEADERS`; if the finance team's format is meant to hold, the test is asserting the wrong thing and should expect `mobile`.

The renamed files, 23 occurrences in total:

- `src/accounts/models.py`, `src/accounts/forms.py`, `src/accounts/serializers.py` — 11
- `src/notify/sms.py` — 3
- `tests/test_accounts.py`, `tests/test_notify.py` — 9

`tests/test_accounts.py` and `tests/test_notify.py` pass, 20 tests. The full suite is at one failure, the CSV header one above; I have not re-run it since, so that count is from the run before I narrowed to the two files.