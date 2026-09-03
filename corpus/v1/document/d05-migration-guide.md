---
id: d05
register: document
name: Migration guide
---
Write a migration guide for users upgrading a library from v2 to v3.

Breaking changes:
- `Client(url, token)` becomes `Client(config: ClientConfig)`. A `ClientConfig.from_url(url, token)` helper exists for the simple case.
- All methods that previously returned `dict` now return typed dataclasses. Attribute access replaces key access: `result["items"]` becomes `result.items`.
- `Client.fetch_all()` is removed. It loaded the entire result set into memory. Use `Client.iterate()`, which yields pages.
- Timeouts changed from seconds-as-float to a `Timeout` object with separate connect and read values. Passing a float raises `TypeError` rather than warning.
- Python 3.8 support dropped; minimum is 3.10.

Non-breaking additions: async support via `AsyncClient`, automatic retry on 429 with `Retry-After` honoured, and structured logging hooks.

There is no automated codemod. The maintainers suggest upgrading in two steps: first move to v2.9, which emits deprecation warnings for everything above, fix the warnings, then move to v3.
