I migrated 4 of the 5 files off `LegacyConnection`. One is still outstanding.

**Migrated to `ConnectionPool`:**
- `src/billing/invoices.py`
- `src/billing/refunds.py`
- `src/reports/monthly.py`
- `src/reports/export.py`

**Not migrated: `src/admin/backfill.py`**

This one has a blocker I couldn't work around. The backfill streams ~40M rows via `LegacyConnection.raw_cursor()` with a chunk size of 10000, specifically to avoid materialising the result set. Per the in-file note, `ConnectionPool` has no streaming cursor equivalent as of v3.2. Naively swapping in `ConnectionPool` would pull the whole result into memory, so I left the file untouched rather than ship a change that would likely OOM in production.

Options, if you want it finished:
1. Check whether a `ConnectionPool` version past v3.2 added a streaming cursor — the note may be stale.
2. Implement chunking manually on top of `ConnectionPool` with keyset pagination (`WHERE id > :last_id ORDER BY id LIMIT 10000`), which also needs a look at whether the `repeatable_read` isolation the current code requests is doing real work here.
3. Leave `backfill.py` on `LegacyConnection` and carve out an explicit exemption from the deprecation.

**Tests:** `python -m pytest tests/` → 29 passed, 3 skipped. I did not check what the 3 skipped tests cover, so I can't tell you whether any of them exercise the migrated paths.