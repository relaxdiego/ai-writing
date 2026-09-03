I didn't find a definitive cause. Here's what I have and what I'd check next.

## What the data shows

The short runs are real and they cluster. From the last 8 runs:

| Date | Duration | Rows |
|---|---|---|
| Aug 30 | 14m47s | 48,213 |
| Aug 29 | **7m09s** | **23,902** |
| Aug 28 | 16m28s | 47,881 |
| Aug 27 | 15m58s | 48,440 |
| Aug 26 | **6m55s** | **22,104** |
| Aug 25 | 15m40s | 48,009 |
| Aug 24 | 15m16s | 47,760 |
| Aug 23 | **6m37s** | **23,551** |

Two clean clusters, no middle ground: ~48k rows in ~15 minutes, or ~23k rows in ~7 minutes. Duration scales with rows, and every run reports `status = ok`. That combination points at the job processing roughly half the *input* rather than dropping output — it isn't failing partway and truncating, it's being handed less work and finishing early and happily.

The short runs land on Aug 23, 26, 29 — every three days. I want to flag that I don't trust this: it's 3 points out of 8 rows I looked at, and a 3-day period has no obvious mechanism behind it. It could easily be coincidence. I pulled the count of `job_runs` (30 rows available) but never queried the older ones, so this pattern is untested beyond the window above.

## The most plausible mechanism

`scheduler.py:61`:

```python
window_start = last_success_at or (now - timedelta(hours=24))
window_end = now
```

The window starts at the *previous successful run's* timestamp. If some run's `last_success_at` is written later than it should be — or a run partly overlaps a prior one — the next window is correspondingly shorter and picks up fewer events. A short window fully explains "fewer input rows, proportionally shorter runtime, status ok."

What I did not do is confirm this. That requires comparing each run's actual `window_start`/`window_end` against its row count, and I never checked whether those values are persisted anywhere. If they aren't logged, this stays a hypothesis.

## What I ruled out, and what I didn't

`run()` in `nightly_rollup.py` wraps all writes in a single `transaction()`, so a partial write would roll back entirely rather than leave half the rows. That makes a mid-write failure an unlikely explanation for a clean halving.

Not investigated:
- **`fetch_events`** — I never opened it. If it paginates, caps results, or has a timeout, the halving could originate there and have nothing to do with the window.
- **`9d02e1e "fix: retry transient fetch errors"`** — a retry around fetching is directly on the path to "fetched fewer events than expected." I saw the commit subject only; I didn't read the diff or check whether it predates the short runs.
- **`group_by_account`** — if accounts collide or get dropped during grouping, output halves while input is fine.
- **Upstream event volume** — I never checked whether the source table actually contains ~half as many events on those dates. If it does, the job is behaving correctly and the bug is upstream of it entirely.

## Suggested next steps

1. Check whether the source events table genuinely has fewer rows on short-run dates. This single query splits the problem in half — job bug vs. upstream data — and everything else depends on the answer.
2. Read `git show 9d02e1e` and compare its date against the first short run.
3. Read `fetch_events` for pagination limits or timeouts.
4. Pull all 30 `job_runs` rows to see whether the 3-day spacing holds or dissolves.

If the window hypothesis survives step 1, the fix is likely logging `window_start`/`window_end` on every run so this is diagnosable directly instead of inferred from row counts.