The rename is done in six of the seven files, but I stopped short in `src/admin/export_csv.py`, and the test suite is currently red because of it.

`mobile` is now `phone` across the model, form, and serializer in `src/accounts/`, in `src/notify/sms.py`, and in `tests/test_accounts.py` and `tests/test_notify.py` — 23 occurrences. Those two test files pass, 20 tests.

The holdout is the CSV header list at `src/admin/export_csv.py:40`:

```python
HEADERS = ["id", "name", "mobile", "signed_up"]

def row_for(user):
    # These column names are the file format the finance team imports.
    # Changing them changes the file other people's spreadsheets read.
    return [user.id, user.name, user.phone, user.signed_up]
```

The attribute access had to change, since `user.mobile` no longer exists. The string in `HEADERS` is a different thing: it's not a reference to the field, it's the column name in a file other people's tooling reads, and the comment says so explicitly. Renaming it would change the output format for the finance team's import, which is outside what a field rename implies, so I left it and am flagging it instead. Whether that spreadsheet contract can absorb the change is something only you can check.

That leaves `tests/test_export.py::test_csv_headers` failing on `assert 'phone' in headers`. That test never contained the literal `mobile` — it wasn't in the grep hits — so it appears to derive the expected header from the model's field name rather than hard-coding it, which means my rename in `models.py` is what turned it red. Nothing I can do to that test fixes the underlying question: either the header string becomes `"phone"` and the finance team's importer needs updating, or the header stays `"mobile"` and the test needs to assert the literal string rather than the field name.