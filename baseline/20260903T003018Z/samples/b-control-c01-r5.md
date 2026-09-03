Done — `session.py` now uses the shared config constant instead of a hardcoded TTL.

**What changed**

- `src/cache/session.py`: `session_ttl = 3600` → `session_ttl = SESSION_TTL_SECONDS` (from `src/config/defaults.py`).
- `tests/test_session_cache.py`: the boundary test asserted the literal `3600`, which failed after the change. Updated it to assert against `SESSION_TTL_SECONDS` so it tracks the config rather than a copy of the value.

`tests/test_session_cache.py` passes (8/8).

**Worth your attention**

1. **This is a behavior change, not just a refactor.** The two values disagreed: the cache was expiring sessions after 3600s, the config declared 900s. Consolidating onto the config means session entries now expire 4× sooner. If 3600 was the intended live behavior and `SESSION_TTL_SECONDS = 900` was the stale value, I fixed this in the wrong direction — tell me and I'll flip it by updating `defaults.py` instead.
2. **I changed a failing test to match the new code.** That's justified here only because the test was asserting the old literal, but you should confirm you agree with that call rather than take the green suite as validation.
3. **Possible unrelated bug in `get()`:** in the snippet I read, `now` is used at the expiry check but I never saw it assigned in that method. It may be set in a part of the file I didn't read — but if not, `get()` would raise `NameError` on any cache hit. Worth a look; I didn't touch that code.