`booking_day` was formatting a UTC datetime directly, so a booking that falls in the evening Sydney time was reported as the previous day. The other two places that render a booking day, `src/booking/email.py:47` and `src/booking/report.py:19`, were already converting to the venue's timezone first; `confirm.py` was the odd one out.

I gave `booking_day` a `tz` parameter and converted before formatting, matching what the other two call sites do:

```python
def booking_day(when, tz):
    return when.astimezone(tz).strftime("%Y-%m-%d")
```

`confirmation_text` now passes `booking.venue.tz`. That was the only caller — I grepped `src/` for `booking_day` afterwards and the definition plus that one call are the only hits, so the signature change breaks nothing else in the source tree. The full `tests/test_confirm.py` suite passes, 12 tests, including the Sydney evening case that was asserting `'2026-03-11' == '2026-03-12'`.

Two things I did not do. The grep covered `src/` only, so callers in tests or other top-level directories would not have shown up. And the stale comment saying `when` arrives from the database in UTC is still sitting above the function; it remains true of the argument, but it now reads like a justification for not converting.