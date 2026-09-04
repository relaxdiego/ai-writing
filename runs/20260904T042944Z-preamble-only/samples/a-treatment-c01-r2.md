`booking_day` in `src/booking/confirm.py` was formatting the raw UTC timestamp, so a booking at 2026-03-12 09:00 Sydney time (2026-03-11 22:00 UTC) confirmed as the 11th. That was the failure in `test_evening_booking_in_sydney`. The comment above the function recorded that `when` arrives from the database in UTC, but nothing ever converted it, so the date rolled back for any venue far enough east in the evening. It now takes the venue timezone and converts before formatting:

```python
def booking_day(when, tz):
    return when.astimezone(tz).strftime("%Y-%m-%d")
```

The one caller, `confirmation_text`, passes `booking.venue.tz`; a grep for `booking_day` across `src/` confirms there are no others, so the signature change is contained. The full `tests/test_confirm.py` suite passes, 12 tests.

The two other places that build a day string, `email.py:47` and `report.py:19`, were already converting through `venue.tz` before formatting, which is why the bug only ever showed up in the confirmation path.