`booking_day` was formatting a UTC datetime directly, so any booking whose local date differed from the UTC date came out wrong; the confirmation for an evening Sydney booking read 2026-03-11 instead of 2026-03-12. It now takes the venue timezone and converts before formatting:

```python
def booking_day(when, tz):
    return when.astimezone(tz).strftime("%Y-%m-%d")
```

The comment in `confirm.py` said `when` arrives from the database in UTC, which was accurate, but nothing downstream acted on it. Grepping for the other date-formatting sites showed that `email.py:47` and `report.py:19` both already call `astimezone(venue.tz)` before formatting, so the confirmation path was the only place the conversion was missing rather than a pattern repeated across the module.

Changing the signature meant updating the caller, `confirmation_text`, to pass `booking.venue.tz`. A grep for `booking_day` across `src/` confirms those two are the only references, so no other call site is left on the old one-argument form. The full `tests/test_confirm.py` run passes at 12 tests, including `test_evening_booking_in_sydney`, which was the failing case.