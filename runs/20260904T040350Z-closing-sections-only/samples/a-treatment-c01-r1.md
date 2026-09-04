`booking_day` in `src/booking/confirm.py` formatted the timestamp straight out of the database, which is UTC, so any booking late enough in the day at a venue ahead of UTC printed the day before. The failing test `test_evening_booking_in_sydney` showed exactly that, asserting `'2026-03-11' == '2026-03-12'`. The function now takes the venue timezone and converts before formatting, matching what `email.py:47` and `report.py:19` were already doing:

```python
def booking_day(when, tz):
    return when.astimezone(tz).strftime("%Y-%m-%d")
```

The signature change is safe because `confirmation_text` is the only caller in `src/`; I passed `booking.venue.tz` there and grepped afterwards to confirm nothing else calls it. The full `tests/test_confirm.py` run passes, 12 tests.