Migrated 4 of the 5 files off `LegacyConnection`:

- `src/billing/invoices.py`
- `src/billing/refunds.py`
- `src/reports/monthly.py`
- `src/reports/export.py`

`src/admin/backfill.py` is still on `LegacyConnection` and I left it alone. It uses `raw_cursor()` to stream 40M rows in chunks without materialising them, and per the comment in the file, `ConnectionPool` has no streaming cursor equivalent as of v3.2. Swapping it would either blow memory or need a different chunking strategy written from scratch — a design decision rather than a mechanical migration, so it needs your call.

Test suite passes: 29 passed, 3 skipped. Note that the pass doesn't tell you much about the migrated code specifically — I didn't check whether those four modules have real coverage, and the 3 skips are unexamined.

Options for `backfill.py`: keep it on `LegacyConnection` with an explanatory comment and a deprecation exemption, or reimplement the streaming with keyset pagination over `ConnectionPool`. Which do you want?