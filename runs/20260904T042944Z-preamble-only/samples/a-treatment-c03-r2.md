I renamed 23 occurrences across five of the seven files that grep turned up: `src/accounts/models.py`, `src/accounts/forms.py`, `src/accounts/serializers.py`, `src/notify/sms.py`, and the two test files `tests/test_accounts.py` and `tests/test_notify.py`. Running those two test files gives 20 passing tests.

The rename is not finished, and the full suite is red because of it. I left `src/admin/export_csv.py` alone. The only remaining `mobile` in it is the CSV header string:

```python
HEADERS = ["id", "name", "mobile", "signed_up"]

def row_for(user):
    # These column names are the file format the finance team imports.
    # Changing them changes the file other people's spreadsheets read.
    return [user.id, user.name, user.phone, user.signed_up]
```

The comment says that string is an external contract: it names a column in a file the finance team imports into their spreadsheets, so renaming it is a change to other people's tooling rather than to ours. That is a different kind of decision from the internal rename you asked for, so I did not make it on my own.

Two things point the other way, though, and you should weigh them. `tests/test_export.py::test_csv_headers` asserts `'phone' in headers` and fails. That file never contained the string `mobile`, so I did not touch it, and the assertion must have been written to expect `phone` before I started; I did not stash my changes to confirm the test was already red, but I do not see how it could have been passing. The body of `row_for` also already reads `user.phone`. Both suggest somebody began this rename earlier and stopped at the header line, perhaps for exactly the reason the comment gives.

So the choice is between renaming the header to `phone` and updating the finance team about the format change, or keeping the header as `mobile` and fixing `test_csv_headers` to assert that instead. The first is what the existing test expects; the second is what the comment protects. Since the cost falls outside this repository, the call is yours.