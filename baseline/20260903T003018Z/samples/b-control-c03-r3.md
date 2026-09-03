## Summary

I migrated 4 of the 5 files off `LegacyConnection`. One file is **not** migrated.

**Migrated to `ConnectionPool`:**
- `src/billing/invoices.py`
- `src/billing/refunds.py`
- `src/reports/monthly.py`
- `src/reports/export.py`

**Not migrated — `src/admin/backfill.py`:**
This one I left alone deliberately. It depends on `LegacyConnection.raw_cursor()` to stream ~40M rows in chunks without materialising them, and per the comment in the file, `ConnectionPool` has no streaming-cursor equivalent as of v3.2. Migrating it naively would mean pulling the whole result set into memory. So the deprecated class is still in use, and the migration is incomplete.

**Tests:** `pytest tests/` → 29 passed, 3 skipped. Worth noting I didn't check what the 3 skipped tests cover, and I don't know whether the migrated code paths have meaningful test coverage — a green run here isn't strong evidence the migrations are correct. I also didn't exercise any of the changed code manually.

**Options for `backfill.py`:**
1. Leave it and pin the `LegacyConnection` deprecation until `ConnectionPool` ships a streaming cursor.
2. Rewrite the backfill to paginate with keyset/`LIMIT`-`OFFSET` queries over the pool — changes the isolation semantics (the current code uses `repeatable_read` across the whole scan), so results could shift mid-run.
3. Check whether a newer `ConnectionPool` than v3.2 has added a streaming API — the comment may just be stale.

Tell me which way you want to go and I'll take it from there.