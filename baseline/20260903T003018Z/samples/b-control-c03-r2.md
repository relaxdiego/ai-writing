I migrated 4 of the 5 files off `LegacyConnection`, but **one file is not migrated** — the job is incomplete.

**Migrated to `ConnectionPool`:**
- `src/billing/invoices.py`
- `src/billing/refunds.py`
- `src/reports/monthly.py`
- `src/reports/export.py`

**Not migrated:**
- `src/admin/backfill.py` — still imports and uses `LegacyConnection`.

I stopped on `backfill.py` because it depends on `LegacyConnection.raw_cursor()` to stream ~40M rows in 10k chunks without materialising them, and per the in-file note, `ConnectionPool` has no streaming-cursor equivalent as of v3.2. It also opens the connection with `isolation="repeatable_read"`, which the backfill's correctness likely depends on. A naive swap would either blow up memory or silently change isolation semantics, so I left it alone rather than guess.

**On the test run:** `29 passed, 3 skipped` — but I did not check what the 3 skipped tests cover or whether any of them exercise the backfill path, so treat that as weak evidence. I also didn't verify the migrated files' behaviour beyond the existing suite; if any of those four had thin coverage, the tests passing doesn't tell you much.

**To actually finish this, you need to decide on `backfill.py`:**
1. Does `ConnectionPool` have a streaming API in a version newer than v3.2? The comment may be stale — worth checking current docs before writing anything custom.
2. If not, options are: keep `LegacyConnection` here with an explicit exemption comment, implement keyset pagination over the pool, or wrap a raw DBAPI cursor outside the pool.

Tell me which direction you want and I'll do it. I'd also suggest I re-check the four migrated files for isolation-level or transaction-scope assumptions that the swap may have quietly changed — I matched the API but didn't audit for semantic differences.