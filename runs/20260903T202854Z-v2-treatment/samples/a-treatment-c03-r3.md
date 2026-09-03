One test is failing, and I left one file unchanged pending a decision from you.

The rename itself is done: 23 occurrences across five files, in `src/accounts/models.py`, `forms.py` and `serializers.py` (11), `src/notify/sms.py` (3), and the two test files (9). Those tests pass, 20 of them.

The file I stopped at is `src/admin/export_csv.py`, where `HEADERS` still has `"mobile"` in it. The comment above `row_for` says the column names are the file format the finance team imports and that changing them changes what other people's spreadsheets read, so I didn't want to alter it as part of a mechanical rename. The complication is that `tests/test_export.py::test_csv_headers` asserts `'phone' in headers` and now fails. That test never contained the string `mobile`, so it wasn't in my grep and I haven't edited it; the repo's own test already expected the new header name, which contradicts the comment sitting next to it. One of the two is stale and I can't tell which from here.

Related, and probably the same story: `row_for` already returned `user.phone` before I started, while `HEADERS` still said `"mobile"`. Against the old model that line would have raised `AttributeError`, so it looks like a partial rename was already in flight. My change is what makes that line valid, but the header label and the value underneath it still disagree.

So the full suite is at one failure, `test_csv_headers`, and it stays there until the CSV header question is settled.