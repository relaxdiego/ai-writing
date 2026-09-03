Done — the session cache now uses the configured TTL instead of a hardcoded one.

**Changes:**
- `src/cache/session.py`: `session_ttl = 3600` → `session_ttl = SESSION_TTL_SECONDS`
- `tests/test_session_cache.py`: updated `test_expiry_boundary` to assert against `SESSION_TTL_SECONDS` rather than the literal `3600`

`tests/test_session_cache.py` passes: 8 passed.

**Worth knowing:** this is a real behavior change, not just a refactor. `SESSION_TTL_SECONDS` in `src/config/defaults.py` is 900, so cached sessions now expire after 15 minutes instead of 60. If 3600 was the intended lifetime, the fix should be to change the default in `defaults.py` rather than keep 900 — let me know which value you actually want.

**One thing I noticed but did not touch:** in `SessionCache.get()`, the expiry check reads `if now - entry.created > self.session_ttl`, but I never saw `now` assigned inside that method in the range I read (lines 80–95). It may be bound above line 80 or be a module-level import, but if it isn't, that comparison would raise `NameError` at runtime. The passing tests suggest it resolves somehow, but I didn't verify it — worth a quick look.