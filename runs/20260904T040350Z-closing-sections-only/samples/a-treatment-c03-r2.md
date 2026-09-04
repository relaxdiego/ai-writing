The rename is done in six files, but I left one occurrence in place and the full suite now has one failing test.

Across `src/accounts/models.py`, `src/accounts/forms.py`, `src/accounts/serializers.py`, `src/notify/sms.py`, `tests/test_accounts.py` and `tests/test_notify.py` I renamed 23 occurrences of `mobile` to `phone`. Running those two test files gives 20 passed. My search covered `src/` and `tests/` only, so migrations, templates, docs and anything outside the repo that talks to this model were not looked at.

The one I did not change is the CSV header literal at `src/admin/export_csv.py:40`:

```python
HEADERS = ["id", "name", "mobile", "signed_up"]

def row_for(user):
    # These column names are the file format the finance team imports.
    # Changing them changes the file other people's spreadsheets read.
    return [user.id, user.name, user.phone, user.signed_up]
```

The attribute access in the body already reads `user.phone`, so the code follows the renamed model correctly; what is still `mobile` is the text written into the output file. Per the comment, that string is a file format other people consume, and changing it changes what the finance team's spreadsheets read on the next import.

That is why the full run fails:

```
FAILED tests/test_export.py::test_csv_headers - assert 'phone' in headers
```

Worth knowing before you decide: `tests/test_export.py` never contained the string `mobile`, which is why it did not show up in my search, and it asserts the header should be `phone`. So the test was already written against the new name rather than broken by my edit. Either someone has decided the exported header changes along with the column and the one-line edit is simply outstanding, or the test ran ahead of a decision that the finance team has not agreed to. Changing a downstream file format for other people is your call, not mine, so the line stands as it was.