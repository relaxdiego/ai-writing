Pointed the session cache at the shared config constant.

**Changes**
- `src/cache/session.py:14` — `session_ttl = 3600` → `session_ttl = SESSION_TTL_SECONDS`
- `tests/test_session_cache.py` — the corresponding assertion, same substitution

`tests/test_session_cache.py` passes, 8 tests.

**One thing to confirm before this ships:** this is a live behavior change, not just a cleanup. `SESSION_TTL_SECONDS` is 900, so session entries now expire after 15 minutes instead of an hour. The test failure I hit (`assert 3600 == 900`) was that change being caught, and I updated the test to match the new value rather than treating it as a regression. If 3600 was the intended TTL and `defaults.py` is the stale one, the fix belongs on the other side — set `SESSION_TTL_SECONDS = 3600` and revert the test edit.

Also worth a look while you're in that file: `get()` at `src/cache/session.py:84` references `now` without any assignment in the enclosing lines I read (80–95). The tests pass, so it's resolving from somewhere, but it isn't a local.