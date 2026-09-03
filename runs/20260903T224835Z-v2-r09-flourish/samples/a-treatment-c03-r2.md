The rename is done, but I left one test failing: `tests/test_export.py::test_csv_headers`.

Twenty-three occurrences of `mobile` became `phone` across `src/accounts/models.py`, `src/accounts/forms.py`, `src/accounts/serializers.py`, `src/notify/sms.py`, `tests/test_accounts.py` and `tests/test_notify.py`. Those two test files pass, twenty tests.

The exception is `src/admin/export_csv.py`, which uses the name in two different ways:

```python
HEADERS = ["id", "name", "mobile", "signed_up"]

def row_for(user):
    # These column names are the file format the finance team imports.
    # Changing them changes the file other people's spreadsheets read.
    return [user.id, user.name, user.phone, user.signed_up]
```

I renamed the attribute access, since the model field is now `phone` and that line would otherwise break. I did not touch the string in `HEADERS`, because the comment above it says those names are an output format other people's spreadsheets read, which is a separate contract from the database column you renamed.

So the last full-suite run stands at one failure: `test_csv_headers` asserts `'phone' in headers`, and the header is still `"mobile"`. Which way to resolve it depends on something I can't see from the code:

- If the CSV header is meant to track the column name, change the literal to `"phone"` and the test passes unmodified.
- If the finance import format is fixed, the header stays `"mobile"` and `test_csv_headers` is the thing that needs correcting, since it currently encodes the opposite expectation.

I stopped there rather than guess, because one of those two choices silently breaks a file outside this repository.