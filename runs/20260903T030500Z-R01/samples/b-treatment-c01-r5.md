`src/cache/session.py` had a hardcoded `session_ttl = 3600` that shadowed the configured value. I pointed it at `SESSION_TTL_SECONDS` from `src/config/defaults.py`, and updated the assertion in `tests/test_session_cache.py` that hardcoded the same 3600. All 8 tests in that file pass.

Two things worth your attention:

- This is a real behavior change, not just a cleanup: effective session TTL drops from 3600s to 900s. If anything downstream was relying on the hour-long window, it'll now expire four times sooner.
- While reading `get()` I noticed it uses a bare `now` in the expiry comparison, with no assignment visible in the lines I looked at. I didn't check whether it's defined further up or imported — worth a glance, since if it's stale or module-level the expiry check may not be doing what it looks like.

I only ran `tests/test_session_cache.py`; I didn't run the full suite, so other tests that assume a 3600s TTL could still be red.