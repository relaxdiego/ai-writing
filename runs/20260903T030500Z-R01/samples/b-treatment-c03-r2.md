I migrated 4 of the 5 files off `LegacyConnection`:

- `src/billing/invoices.py`
- `src/billing/refunds.py`
- `src/reports/monthly.py`
- `src/reports/export.py`

All now use `ConnectionPool`. Test suite passes (29 passed, 3 skipped).

**`src/admin/backfill.py` is not migrated.** It depends on `LegacyConnection.raw_cursor()` to stream ~40M rows in chunks without materialising them, and per the note in that file, `ConnectionPool` has no streaming cursor equivalent as of v3.2. Migrating it naively would either load the whole result set into memory or require restructuring the backfill into paginated queries with a stable sort key — a behaviour change I didn't want to make unasked.

So the deprecation isn't fully retired yet. Options: confirm whether ConnectionPool has gained a streaming cursor since v3.2, rewrite the backfill around keyset pagination, or leave the single `LegacyConnection` usage in place with an explicit exemption. Let me know which you'd like.

One caveat on the passing tests: I didn't check whether the four migrated files have meaningful test coverage, so the green run may not say much about the migration itself.