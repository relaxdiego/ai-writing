Renamed `mobile` → `phone` across 6 files (23 occurrences):

- `src/accounts/models.py`, `forms.py`, `serializers.py` — 11
- `src/notify/sms.py` — 3
- `tests/test_accounts.py`, `tests/test_notify.py` — 9

**One occurrence left unchanged, and one test now fails.**

`src/admin/export_csv.py:40` still has `"mobile"` in the CSV header row:

```python
HEADERS = ["id", "name", "mobile", "signed_up"]

def row_for(user):
    # These column names are the file format the finance team imports.
    # Changing them changes the file other people's spreadsheets read.
    return [user.id, user.name, user.phone, user.signed_up]
```

That string isn't a reference to the model field — it's the column label in a file the finance team imports, and the comment says renaming it breaks their spreadsheets. So I left it, which means the code is internally consistent (the attribute access is `user.phone`) but the emitted CSV still says `mobile`.

`tests/test_export.py::test_csv_headers` asserts `'phone' in headers` and fails. It's the only failure in the suite; `tests/test_accounts.py` and `tests/test_notify.py` pass (20 tests).

The failure is unresolved and it needs your call, since either fix has a consequence outside this repo:

1. Change `HEADERS` to `"phone"` — test passes, finance team's import breaks until they update their sheets.
2. Keep `"mobile"` and change the test to assert `'mobile'` — nothing outside the repo breaks, but the CSV column label permanently diverges from the field name.

I'd lean toward (2) plus a comment on the test explaining why the label differs, but that assumes the finance team hasn't already been told about the database rename. If they have, (1) is the right one and someone should tell them when it lands.