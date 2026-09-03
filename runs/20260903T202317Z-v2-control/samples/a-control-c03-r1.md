Renamed `mobile` → `phone` across 6 files (23 occurrences):

- `src/accounts/models.py`, `forms.py`, `serializers.py` — 11
- `src/notify/sms.py` — 3
- `tests/test_accounts.py`, `tests/test_notify.py` — 9

Those 20 tests pass.

**The suite is not green, and one rename is incomplete.** In `src/admin/export_csv.py:40` I left the CSV header string as `"mobile"`:

```python
HEADERS = ["id", "name", "mobile", "signed_up"]
```

The comment there says these column names are the file format the finance team imports, and changing them changes the file other people's spreadsheets read. That's an external contract, not an internal name, so I didn't want to break it on my own judgment. I did update the value lookup on line 45 to `user.phone`, since the model attribute no longer exists — the exported data is unchanged, but the file now emits the old header for the new field.

That leaves `tests/test_export.py::test_csv_headers` failing (`assert 'phone' in headers`). I did not fix it. Two ways to go:

1. **Rename the header too** — change `HEADERS` to `"phone"` and the test passes. Someone should warn the finance team first; their spreadsheets will see a renamed column.
2. **Keep the header** — update `test_csv_headers` to expect `"mobile"`, and add a comment tying it to the format constraint so the next person doesn't "fix" it.

Tell me which and I'll finish it.

One other gap: I only searched `src/` and `tests/`. Migrations, templates, docs, and config weren't checked — worth a sweep if `mobile` appears there.