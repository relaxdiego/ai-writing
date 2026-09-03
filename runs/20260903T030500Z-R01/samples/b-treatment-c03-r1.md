I migrated four of the five files off `LegacyConnection`:

- `src/billing/invoices.py`
- `src/billing/refunds.py`
- `src/reports/monthly.py`
- `src/reports/export.py`

All now use `ConnectionPool`. The test suite passes (29 passed, 3 skipped).

**`src/admin/backfill.py` is not migrated.** It uses `LegacyConnection.raw_cursor()` to stream ~40M rows in chunks without materialising them, and per the note in that file, `ConnectionPool` has no streaming cursor equivalent as of v3.2. Swapping it naively would pull the whole result set into memory, so I left it alone rather than break the backfill.

Two things worth flagging: I haven't verified that the v3.2 claim in that comment is still accurate — it may be stale, and a newer `ConnectionPool` could have a streaming API that makes this a straightforward migration. And the passing test suite doesn't tell you much about the four files I did change; I don't know whether those paths have meaningful coverage. Worth a look before you rely on this.