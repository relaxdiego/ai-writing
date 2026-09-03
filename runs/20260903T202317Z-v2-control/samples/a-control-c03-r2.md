Renamed `mobile` → `phone` across the code and tests, with one deliberate exception that leaves the suite red.

**Changed (23 occurrences, 5 files):**
- `src/accounts/models.py`, `forms.py`, `serializers.py` — 11
- `src/notify/sms.py` — 3
- `tests/test_accounts.py`, `tests/test_notify.py` — 9

`tests/test_accounts.py` and `tests/test_notify.py` pass — 20 tests.

**Not changed:** `src/admin/export_csv.py:40` still has `"mobile"` in `HEADERS`. That string isn't a field reference — it's a CSV column name, and the comment right below it says the finance team's spreadsheets import this file. Renaming it changes the output format for people outside this repo, which is beyond a code rename. The attribute access on line 45 was already `user.phone`, so the module reads the right field either way.

**The suite is currently failing:** `tests/test_export.py::test_csv_headers` asserts `'phone' in headers` and fails against the unchanged `"mobile"` header. That test file never contained the string `mobile`, so it wasn't in my grep and I didn't touch it — it appears to have been written expecting the header to be renamed too.

So the two signals conflict: the code comment says don't change the header, the test says it should already be `phone`. I stopped rather than pick one. Which is right?

- If the finance export should follow the rename, I'll change `HEADERS` and the suite goes green — but the next file you send them has a different column name, so someone should warn them.
- If the header must stay `mobile`, `test_csv_headers` needs updating to assert that, and it's worth a comment noting the header intentionally diverges from the field name.