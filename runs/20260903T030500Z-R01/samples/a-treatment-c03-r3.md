Migrated four of the five files off `LegacyConnection`:

- `src/billing/invoices.py`
- `src/billing/refunds.py`
- `src/reports/monthly.py`
- `src/reports/export.py`

All now use `ConnectionPool`. Test suite passes: 29 passed, 3 skipped.

**`src/admin/backfill.py` is not migrated.** It uses `LegacyConnection.raw_cursor()` to stream ~40M rows in chunks without materialising them, and per the note in that file, `ConnectionPool` has no streaming cursor equivalent as of v3.2. Swapping it over would either load the whole result set into memory or require restructuring the backfill around keyset pagination — a design decision beyond a mechanical migration, so I left it alone.

Two things worth noting: I verified the migration only via the existing test suite, and the 3 skipped tests may cover paths I touched — I didn't check which. And the `ConnectionPool` streaming gap is my read of that file's comment, not something I confirmed against the `ConnectionPool` source.

If you want `backfill.py` finished too, tell me which direction you'd prefer and I'll do it.