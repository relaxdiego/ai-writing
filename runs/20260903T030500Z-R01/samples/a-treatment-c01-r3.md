`SessionCache.session_ttl` was hardcoded to 3600 while `src/config/defaults.py:31` defines `SESSION_TTL_SECONDS = 900`. I pointed the class attribute at the config constant (`src/cache/session.py:14`), so expiry in `get()` now uses 900s.

One test, `test_expiry_boundary`, asserted the literal 3600; I updated it to compare against `SESSION_TTL_SECONDS` too. All 8 tests in `tests/test_session_cache.py` pass.

Worth flagging: this is a real behavior change, not just a refactor — sessions now expire after 15 minutes instead of an hour. I assumed the config value was the intended one since the constant existed and was unused; if 3600 was correct, the fix is to change `defaults.py` instead.