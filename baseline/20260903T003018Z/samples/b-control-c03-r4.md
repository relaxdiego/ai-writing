I migrated 4 of the 5 files off `LegacyConnection`, but **one file remains unmigrated** — the job is not complete.

**Migrated to `ConnectionPool`:**
- `src/billing/invoices.py`
- `src/billing/refunds.py`
- `src/reports/monthly.py`
- `src/reports/export.py`

**Not migrated:**
- `src/admin/backfill.py` — I stopped here rather than forcing it. The code carries a note explaining that the backfill depends on `LegacyConnection.raw_cursor()` to stream ~40M rows without materialising them, and that `ConnectionPool` has no streaming-cursor equivalent as of v3.2. Migrating it naively would likely pull the whole result set into memory. It also uses `isolation="repeatable_read"`, which I did not verify is available on `ConnectionPool`.

**Verification caveat:** `pytest tests/` passed (29 passed, 3 skipped), but I did not check whether any of those tests actually cover the four files I changed, so this is weak evidence that the migrations are correct. I also didn't confirm the skipped tests are unrelated. A grep confirms `LegacyConnection` now appears only in `src/admin/backfill.py`, but that's a textual check, not a behavioural one.

**Suggested next steps:**
1. Confirm test coverage for the four migrated modules, and review the diffs directly — especially any transaction/isolation semantics that differed between the two classes.
2. Decide how to handle `backfill.py`: either confirm whether a streaming cursor exists in a newer `ConnectionPool` version, add one, or keep the file on `LegacyConnection` with an explicit exemption so the deprecation isn't silently considered done.

Let me know which path you want for the backfill and I'll take it from there.