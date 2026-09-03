`SessionCache.session_ttl` was hardcoded to `3600`, ignoring the `SESSION_TTL_SECONDS = 900` in `src/config/defaults.py`. I pointed the class attribute at the config constant:

- `src/cache/session.py:14` — `session_ttl = SESSION_TTL_SECONDS`
- `tests/test_session_cache.py` — the boundary test asserted the literal `3600`, so it now asserts against the same constant

`tests/test_session_cache.py` passes, 8/8.

Worth knowing: this is a live behavior change, not just a cleanup. Effective session TTL drops from one hour to 15 minutes, since the config value was never being read before. If 3600 was the intended production lifetime, the fix belongs in `defaults.py` instead.