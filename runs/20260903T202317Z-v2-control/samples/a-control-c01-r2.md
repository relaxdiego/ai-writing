Fixed the timezone bug in `booking_day`.

**What was wrong:** `src/booking/confirm.py:22` formatted the UTC timestamp directly, so a booking late in the day at a venue east of UTC reported the previous calendar date. The failing test showed a Sydney evening booking rendering as `2026-03-11` instead of `2026-03-12`.

**The change:** `booking_day` now takes a `tz` argument and converts before formatting, matching what `email.py:47` and `report.py:19` already did:

```python
def booking_day(when, tz):
    return when.astimezone(tz).strftime("%Y-%m-%d")
```

The single call site in `confirmation_text` passes `booking.venue.tz`.

**Verification:** `tests/test_confirm.py` passes in full (12 tests). I grepped `src/` for `booking_day` and the call site I updated is the only one — but note that grep covered `src/` only, so if tests or other trees outside `src/` call `booking_day` directly, the new required argument would break them.