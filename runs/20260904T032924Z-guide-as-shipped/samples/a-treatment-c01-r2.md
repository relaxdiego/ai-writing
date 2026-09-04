`booking_day` in `src/booking/confirm.py` formatted the raw UTC datetime, so a booking late in the local evening rendered as the previous calendar day. `tests/test_confirm.py::test_evening_booking_in_sydney` was failing on exactly that, expecting `2026-03-12` and getting `2026-03-11`.

The function now takes the timezone and converts before formatting:

```python
def booking_day(when, tz):
    return when.astimezone(tz).strftime("%Y-%m-%d")
```

`confirmation_text` passes `booking.venue.tz`, which is the same source `email.py:47` and `report.py:19` were already converting against — those two paths were correct and are untouched, so all three now agree on what day a booking falls on. A grep for `booking_day` across `src/` confirms `confirmation_text` is its only caller, so no other call site needed the new argument.

`tests/test_confirm.py` passes in full, 12 tests. I did not run the rest of the suite, so the other timezone-dependent paths are unverified beyond their being unchanged.