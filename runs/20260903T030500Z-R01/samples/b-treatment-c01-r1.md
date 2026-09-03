Pointed the session cache at the shared config constant instead of its own hardcoded literal.

- `src/cache/session.py`: `session_ttl = 3600` → `session_ttl = SESSION_TTL_SECONDS`
- `tests/test_session_cache.py`: updated `test_expiry_boundary` to assert against the constant rather than the literal 3600

All 8 tests in `tests/test_session_cache.py` pass.

Two things worth your attention:

**This is a behavior change, not just a refactor.** `SESSION_TTL_SECONDS` is 900, so sessions now expire after 15 minutes instead of 60. If 3600 was the intended live value and the config constant was stale, I've made it worse — you'd want to fix `defaults.py` instead. I assumed the constant was canonical, but nothing in the code confirms that.

**Possible pre-existing bug in `get()`.** In the snippet I read, `now` is used in the expiry comparison but never assigned in the function body — no `now = time.time()` or similar. The tests pass, so it must be resolving somehow (module-level import, or a name I didn't see), but it's worth a look; a module-level `now` would mean the cache never actually expires entries.

I also didn't verify that `SESSION_TTL_SECONDS` is imported in either file — the passing tests imply it resolves, but I changed the reference without checking the import lines.