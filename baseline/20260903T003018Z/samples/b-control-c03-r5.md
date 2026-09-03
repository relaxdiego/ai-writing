I migrated 4 of the 5 files off `LegacyConnection`, but **one file was not migrated** — the job is incomplete.

**Migrated to `ConnectionPool`:**
- `src/billing/invoices.py`
- `src/billing/refunds.py`
- `src/reports/monthly.py`
- `src/reports/export.py`

**Not migrated: `src/admin/backfill.py`**

This one has a blocker I couldn't work around. The backfill uses `LegacyConnection.raw_cursor()` to stream ~40M rows in chunks without materialising them, and per the in-code note, `ConnectionPool` has no streaming cursor equivalent as of v3.2. A naive port would either load 40M rows into memory or silently change the isolation semantics (it currently pins `isolation="repeatable_read"`). I left it on `LegacyConnection` rather than guess.

**Verification caveat:** `pytest tests/` passed (29 passed, 3 skipped), but I don't know whether any of those tests actually exercise the migrated code paths — I didn't check coverage, and I didn't check what the 3 skips were. So the test run is weak evidence that the 4 migrations are correct, not proof. I also didn't run anything against a real database.

**To finish this, you'd need to decide on one of:**
1. Confirm whether a newer `ConnectionPool` version added a streaming cursor (my info is limited to the v3.2 note in the file).
2. Keep `backfill.py` on `LegacyConnection` as a documented exception, with a tracking issue.
3. Rewrite the backfill around a different strategy (e.g. keyset pagination over the pool), which is a real behaviour change and needs its own review.

Want me to dig into the `ConnectionPool` API to check for a streaming option, or verify that the migrated paths are actually covered by tests?