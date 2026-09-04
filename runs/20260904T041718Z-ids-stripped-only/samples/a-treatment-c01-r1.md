The confirmation email was showing the wrong date for bookings that fall late in the day in timezones ahead of UTC. `booking_day` in `src/booking/confirm.py:22` formatted the stored UTC timestamp directly, so a Sydney booking at 09:00 local on 12 March, stored as 22:00 UTC on 11 March, was reported as 11 March. The failing test `test_evening_booking_in_sydney` captured exactly that: `'2026-03-11' == '2026-03-12'`.

I gave `booking_day` a `tz` parameter and converted before formatting, matching what `email.py:47` and `report.py:19` already did:

```python
def booking_day(when, tz):
    return when.astimezone(tz).strftime("%Y-%m-%d")
```

Its only caller, `confirmation_text`, now passes `booking.venue.tz`. A grep for `booking_day` across `src/` confirms those are the only two occurrences, so the signature change breaks nothing else. The full `tests/test_confirm.py` suite passes, 12 tests.

One thing I did not chase: `email.py` and `report.py` each build the same conversion inline rather than calling `booking_day`, and `report.py` goes through `.date().isoformat()` instead of `strftime`. Those produce the same string today, but the duplication is the reason this bug could exist in one place and not the others.