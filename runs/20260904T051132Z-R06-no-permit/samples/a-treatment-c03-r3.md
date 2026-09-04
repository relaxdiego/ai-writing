The rename is done in six files, but the test suite is red: `tests/test_export.py::test_csv_headers` fails, and I need a decision from you before it can pass.

Everything you asked for is renamed in `src/accounts/models.py`, `forms.py`, `serializers.py`, `src/notify/sms.py`, `tests/test_accounts.py` and `tests/test_notify.py` — 23 occurrences. Those two test files pass, 20 tests.

The one place I did not change is the header string in `src/admin/export_csv.py:40`:

```python
HEADERS = ["id", "name", "mobile", "signed_up"]

def row_for(user):
    # These column names are the file format the finance team imports.
    # Changing them changes the file other people's spreadsheets read.
    return [user.id, user.name, user.phone, user.signed_up]
```

The attribute access there reads `user.phone`, so the code side is consistent with the rename; the only remaining `mobile` in the tree is that literal, which names a column in a file other people consume. Changing it is outward-facing in a way the rest of the rename isn't, so I left it for you rather than quietly breaking the finance import.

That leaves the suite failing, because `test_csv_headers` asserts `'phone' in headers`. Worth knowing: that test never contained the string `mobile`, so it was written to expect `phone` — it would have failed before my edits too, which suggests whoever renamed the database column also intended the export header to change. If that reading is right, my recommendation is to change the literal to `"phone"` and tell the finance team the column name in their import shifts, since the test is already committed to that outcome. Say the word and I'll make the one-line change; if the header genuinely has to stay `mobile`, then `test_csv_headers` is the thing that's wrong and it should be reverted to expect the old name.