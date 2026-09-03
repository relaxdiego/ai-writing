Four of the five files are migrated; `src/admin/backfill.py` still uses `LegacyConnection` and I left it that way deliberately.

The backfill streams roughly 40M rows through `LegacyConnection.raw_cursor()` with a chunk size of 10000, and a comment in the file records that `ConnectionPool` has no streaming cursor equivalent as of v3.2. Migrating it mechanically would have meant materialising the whole result set, so the choice is either to stay on the deprecated class until the pool grows a streaming cursor, or to rewrite the backfill around keyset pagination over the existing pool. That call is yours, and it is a different piece of work from this migration.

The files now on `ConnectionPool`:

- `src/billing/invoices.py`
- `src/billing/refunds.py`
- `src/reports/monthly.py`
- `src/reports/export.py`

`pytest tests/` reports 29 passed and 3 skipped. I did not check what the three skips are or whether any of them cover the migrated paths, so the pass count is weaker evidence than it looks; the backfill's streaming behaviour in particular is not something I verified is under test.