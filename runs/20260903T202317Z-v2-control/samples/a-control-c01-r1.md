Fixed the timezone bug in `booking_day`.

**What was wrong:** `src/booking/confirm.py:22` formatted the UTC timestamp directly, so bookings after UTC midnight in ahead-of-UTC venues showed the previous day. The failing test was an evening Sydney booking rendering as `2026-03-11` instead of `2026-03-12`.

**The fix:** `booking_day` now takes a `tz` argument and converts before formatting, matching what `email.py:47` and `report.py:19` already did:

```python
def booking_day(when, tz):
    return when.astimezone(tz).strftime("%Y-%m-%d")
```

The single call site in `confirmation_text` passes `booking.venue.tz`. I grepped `src/` for other callers — there are none, so the signature change is contained.

**Verification:** `tests/test_confirm.py` passes, 12 tests. I only ran that file, not the full suite.