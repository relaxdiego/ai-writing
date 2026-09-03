`booking_day` in `src/booking/confirm.py` was formatting the raw UTC timestamp, so a booking whose local date differs from its UTC date was confirmed for the wrong day. The failing test, `test_evening_booking_in_sydney`, showed an evening Sydney booking reported as 2026-03-11 when it should have been 2026-03-12. The other two places that render a booking day, `src/booking/email.py:47` and `src/booking/report.py:19`, already convert to the venue timezone first, so `confirm.py` was the outlier rather than the pattern.

The fix gives `booking_day` a `tz` parameter and converts before formatting, matching what the email and report paths do:

```python
def booking_day(when, tz):
    return when.astimezone(tz).strftime("%Y-%m-%d")
```

`confirmation_text` now passes `booking.venue.tz`. A grep for `booking_day` across `src/` found only the definition and that one call site, so the signature change has no other callers to update. The full `tests/test_confirm.py` suite passes, twelve tests including the timezone case that was failing.

One thing I did not chase: the stale comment saying "`when` arrives from the database in UTC" is still accurate about the input, but it was sitting there as the justification for not converting. I left it alone since it states a true fact about the argument.