`booking_day` was formatting a UTC datetime directly, so any booking that fell after the UTC/local date boundary reported the wrong day. The failing test was an evening booking in Sydney: stored as `2026-03-11` in UTC, but `2026-03-12` locally. The other two call sites in `email.py` and `report.py` already converted to the venue timezone before formatting, so `confirm.py` was the odd one out.

I gave `booking_day` a required `tz` parameter and converted before formatting, matching what the other two do:

```python
def booking_day(when, tz):
    return when.astimezone(tz).strftime("%Y-%m-%d")
```

The single caller, `confirmation_text`, now passes `booking.venue.tz`. I grepped for `booking_day` across `src/` to confirm there were no other callers left on the old one-argument signature; there were none, so the added parameter breaks nothing. The full `tests/test_confirm.py` suite passes, 12 tests.

One thing worth flagging: I only ran `tests/test_confirm.py`, not the whole suite, and I searched `src/` rather than the repository root, so a caller in tests or another top-level directory would not have shown up in that grep.