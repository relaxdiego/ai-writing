Migrated four of the five files off `LegacyConnection`:

- `src/billing/invoices.py`
- `src/billing/refunds.py`
- `src/reports/monthly.py`
- `src/reports/export.py`

Test suite passes: 29 passed, 3 skipped.

**`src/admin/backfill.py` is not migrated.** It depends on `LegacyConnection.raw_cursor()` to stream 40M rows in chunks without materialising them, and per the note in that file, `ConnectionPool` has no streaming cursor equivalent as of v3.2. Swapping it over would either blow memory or require rewriting the backfill around a different pagination strategy — a bigger change than a mechanical migration, so I stopped rather than guess at it.

Options for that last file: pin the backfill to `LegacyConnection` with an explicit exemption comment, implement keyset pagination over `ConnectionPool`, or check whether a newer `ConnectionPool` adds a streaming cursor. Tell me which and I'll do it.