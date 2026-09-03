Four of the five files are migrated; `src/admin/backfill.py` is not, and it needs your decision.

`invoices.py`, `refunds.py`, `monthly.py` and `export.py` now use `ConnectionPool`, and the suite passes: 29 passed, 3 skipped. A repo-wide grep for `LegacyConnection` returns only `src/admin/backfill.py`.

That file streams roughly 40M rows through `LegacyConnection.raw_cursor()` under a `repeatable_read` isolation level, and a comment in the file records that `ConnectionPool` has no streaming cursor equivalent as of v3.2. I took the comment at face value rather than verifying it against the current `ConnectionPool` API, so the first thing worth checking is whether it is still true. Migrating naively would materialise the whole result set in memory, so I left the file alone. The paths out are:

- Confirm whether v3.2 or later added a streaming cursor; if so, the migration is mechanical.
- Keep `LegacyConnection` in this one file and suppress the deprecation warning at the import site, with a pointer to the upstream gap.
- Rewrite the backfill to paginate by keyset over `ConnectionPool`, which changes the isolation guarantees the current code relies on.

I should also flag that the three skipped tests were skipped before my changes and I did not investigate what they cover; if any of them exercise the backfill path, the passing suite says less about this migration than it appears to.