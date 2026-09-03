The rename is complete in the application code and tests, but I left one line alone and there is a failing test tied to it.

Renamed 23 occurrences across six files: `src/accounts/models.py`, `src/accounts/forms.py`, and `src/accounts/serializers.py` (11), `src/notify/sms.py` (3), and `tests/test_accounts.py` and `tests/test_notify.py` (9). Those two test files pass, 20 of 20.

The line I did not touch is the CSV header literal in `src/admin/export_csv.py:40`:

```python
HEADERS = ["id", "name", "mobile", "signed_up"]
```

The comment directly beneath it says these column names are the file format the finance team imports, and that changing them changes the file other people's spreadsheets read. That string is not a reference to the model field, so the rename does not require it: the row builder on the next lines already reads `user.phone`, and the export works. Renaming a database column is a private change; renaming this header is a change to a published interface, and whether the finance team's importers can absorb it is not something I can determine from the repository.

Against that, `tests/test_export.py::test_csv_headers` asserts `'phone' in headers` and fails. That test never contained the string `mobile`, so my grep did not surface it and I did not edit it, which means somebody wrote it expecting the header to become `phone`. I did not run the suite before making the edits, so I cannot tell you whether it was already failing; nothing I changed touches `HEADERS`, so I believe it was, but that is inference rather than something I observed. The full run is one failure out of 28.

So the code is consistent on `phone` except for that one string, and the disagreement is between a comment saying the header is a fixed external format and a test saying it should change. Resolving it means knowing what the finance team's import actually tolerates, which is your call rather than mine.