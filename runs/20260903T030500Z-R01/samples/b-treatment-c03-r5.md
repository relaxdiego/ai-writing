I migrated 4 of the 5 files off `LegacyConnection`:

- `src/billing/invoices.py`
- `src/billing/refunds.py`
- `src/reports/monthly.py`
- `src/reports/export.py`

Tests pass (29 passed, 3 skipped).

**`src/admin/backfill.py` is not migrated.** It depends on `LegacyConnection.raw_cursor()` to stream ~40M rows in chunks without materialising them, and per the in-file note `ConnectionPool` has no streaming cursor equivalent as of v3.2. Swapping it naively would pull the whole result set into memory. Options: confirm whether a newer `ConnectionPool` version added streaming support, add a streaming cursor to `ConnectionPool`, or leave the backfill on `LegacyConnection` and exempt it from the deprecation. Tell me which you'd prefer and I'll finish it.

Also worth noting: the test run doesn't prove much about the migration — I didn't check whether these four modules have real coverage, so the passing suite may not exercise the changed paths.