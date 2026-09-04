The rename is done everywhere but one line, and the test suite is red because of it.

I renamed 23 occurrences across five files: `src/accounts/models.py`, `forms.py` and `serializers.py` (11), `src/notify/sms.py` (3), and `tests/test_accounts.py` and `tests/test_notify.py` (9). Those two test files pass, 20 tests.

The place I stopped is the CSV export at `src/admin/export_csv.py:40`. The attribute read is now `user.phone`, since that goes through the model, but the header literal still says `"mobile"`:

```python
HEADERS = ["id", "name", "mobile", "signed_up"]
```

The comment above `row_for` says these column names are the file format the finance team imports, and that changing them changes the file other people's spreadsheets read. That is outside what a database column rename implies, so I left it rather than decide it for you.

The cost of leaving it is that the full suite now fails:

```
FAILED tests/test_export.py::test_csv_headers - assert 'phone' in headers
```

That test never contained the string `mobile`, so it is deriving its expectation from somewhere else, most likely the model field. I didn't trace how it builds `headers`. Either way the failure is a direct consequence of the half-rename, and it was passing before I started.

Which way it resolves is your call:

- The exported column is part of the rename. `HEADERS` becomes `"phone"`, the suite goes green, and the next finance import sees a column it doesn't recognise.
- The file format is a contract with people outside this repo. The header stays `"mobile"`, and `test_export.py` is what needs to change, along with a note there saying the export column deliberately diverges from the model field.