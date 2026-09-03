`booking_day` was formatting a UTC datetime without converting it, so any booking whose UTC instant falls on a different calendar day than the venue's local time was reported one day off. The failing Sydney test showed it directly: an evening booking on 2026-03-12 local was still 2026-03-11 in UTC, and the confirmation text said so.

The fix gives `booking_day` a `tz` parameter and converts before formatting, matching what `email.py:47` and `report.py:19` were already doing:

```python
def booking_day(when, tz):
    return when.astimezone(tz).strftime("%Y-%m-%d")
```

The only caller, `confirmation_text`, now passes `booking.venue.tz`. I grepped for other callers of `booking_day` across `src/` and found none, so the signature change is contained. The full `tests/test_confirm.py` suite passes, twelve tests.

One thing I left alone: the stale comment saying `when` arrives from the database in UTC is still accurate about the input, but it now reads as a justification for not converting. I did not touch it because it sits above the line I changed and rewording it is a judgement call about what the function's contract should say.