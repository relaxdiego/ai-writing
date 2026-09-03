Migrated 4 of the 5 files off `LegacyConnection`. One is not done.

**Migrated to `ConnectionPool`:**
- `src/billing/invoices.py`
- `src/billing/refunds.py`
- `src/reports/monthly.py`
- `src/reports/export.py`

**Not migrated: `src/admin/backfill.py`**

It uses `LegacyConnection.raw_cursor()` to stream ~40M rows in 10k chunks without materialising them, under a `repeatable_read` isolation level. Per the comment in the file, `ConnectionPool` (v3.2) has no streaming cursor equivalent. Swapping it for a pooled connection would either pull the full result set into memory or require rewriting the backfill as keyset-paginated batches — a behaviour change, not a mechanical migration, so I stopped rather than guess. `grep -rln "LegacyConnection" src/` still returns this one file.

**Verification:** `pytest tests/` → 29 passed, 3 skipped. I did not check what the 3 skipped tests cover, so I can't tell you whether any of them guard the code I changed.

Options for `backfill.py`, if you want it finished:
1. Rewrite the backfill as keyset pagination over `ConnectionPool` (loses the single-snapshot guarantee `repeatable_read` currently gives across the whole 40M-row scan — matters if rows change mid-run).
2. Check whether a newer `ConnectionPool` version added a server-side/streaming cursor; if so, this stays mechanical.
3. Leave it and add an explicit exemption comment, so the deprecation sweep doesn't keep flagging it.

Tell me which and I'll do it.