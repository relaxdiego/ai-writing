I migrated 4 of the 5 files off `LegacyConnection`, but **one file is not migrated** — the job is incomplete.

**Migrated to `ConnectionPool`:**
- `src/billing/invoices.py`
- `src/billing/refunds.py`
- `src/reports/monthly.py`
- `src/reports/export.py`

**Not migrated:**
- `src/admin/backfill.py` — this one depends on `LegacyConnection.raw_cursor()` to stream ~40M rows without materialising them. Per the comment in that file, `ConnectionPool` has no streaming-cursor equivalent as of v3.2, so a naive swap would likely pull the whole result set into memory. I left it alone rather than guess at a rewrite.

**Verification caveat:** `pytest tests/` passed (29 passed, 3 skipped), but I didn't check whether any of the 4 migrated modules are actually covered by those tests, or what the 3 skips were. A green run here is weak evidence that the migrations are correct — treat it as "nothing obviously broke," not "verified."

**To finish this, you'd need to decide on one of:**
1. Confirm whether `ConnectionPool` (or a newer version) has since gained a streaming cursor — I only have the file's comment as evidence, which may be stale.
2. Rewrite the backfill to page with `LIMIT`/`OFFSET` or keyset pagination over the pool — changes the isolation semantics, since the current code holds one `repeatable_read` transaction across the whole scan.
3. Leave `backfill.py` on `LegacyConnection` and carve out an explicit exception to the deprecation.

Want me to investigate `ConnectionPool`'s current streaming support, or check test coverage on the four migrated files?