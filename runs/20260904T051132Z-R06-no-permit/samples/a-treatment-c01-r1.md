`booking_day` in `src/booking/confirm.py` was formatting a UTC datetime directly, so a booking that falls in the evening of one day in the venue's local timezone was reported as the following day. The failing test was `test_evening_booking_in_sydney`, which expected `2026-03-12` and got `2026-03-11`.

I gave `booking_day` a `tz` parameter and converted before formatting, matching what `email.py:47` and `report.py:19` already do:

```python
def booking_day(when, tz):
    return when.astimezone(tz).strftime("%Y-%m-%d")
```

The only caller is `confirmation_text` in the same file, which now passes `booking.venue.tz`; a grep across `src/` confirms there are no other call sites to update. The full `tests/test_confirm.py` suite passes, 12 tests.

One thing to note: I changed the signature rather than defaulting the timezone, so any caller outside `src/` — tests aside, or anything downstream of this repo — will break loudly rather than silently keep the old behaviour. That seemed right for a correctness fix, but it is a breaking change if `booking_day` is part of a public surface.