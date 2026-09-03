I migrated 4 of the 5 files off `LegacyConnection`:

- `src/billing/invoices.py`
- `src/billing/refunds.py`
- `src/reports/monthly.py`
- `src/reports/export.py`

All now use `ConnectionPool`. Test suite passes (29 passed, 3 skipped).

**`src/admin/backfill.py` is not migrated.** It depends on `LegacyConnection.raw_cursor()` to stream 40M rows in chunks without materialising them, and per the note in the file, `ConnectionPool` has no streaming cursor equivalent as of v3.2. Migrating it naively would pull the whole result set into memory. It still imports `LegacyConnection`, so the deprecated class can't be removed yet.

Options for that last file: check whether a newer `ConnectionPool` version added a streaming cursor, implement keyset pagination over the pool, or leave the backfill on the legacy path with an explicit exemption. Tell me which you'd prefer and I'll do it.