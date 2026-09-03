# Migrating from v2 to v3

v3 is a breaking release. The changes are mechanical but there is no codemod, so every call site has to be touched by hand. This guide walks through the recommended two-step path and then each breaking change individually.

## Recommended upgrade path

Don't jump straight from v2.x to v3. Instead:

1. **Upgrade to v2.9 first.** This release is API-compatible with v2 but emits a `DeprecationWarning` for every pattern that v3 removes.
2. **Run your test suite with warnings visible** and fix everything it reports:
   ```
   python -W error::DeprecationWarning -m pytest
   ```
   Turning warnings into errors is the fastest way to find call sites — each failure points at one line to fix. If that's too aggressive for a large codebase, start with `-W default::DeprecationWarning` and work through the log.
3. **Upgrade to v3** once the warnings are clean. At that point most of your code already works; what remains are the changes v2.9 can't warn about (see [Return types](#return-types) below).

Before any of this, confirm your Python version: **v3 requires Python 3.10 or newer.** Python 3.8 support is dropped. If you're on 3.8, upgrade the interpreter first and get your test suite green there — debugging an interpreter upgrade and a library upgrade simultaneously is unpleasant.

---

## Breaking changes

### 1. Client construction

`Client(url, token)` is replaced by `Client(config: ClientConfig)`.

```python
# v2
client = Client("https://api.example.com", token)

# v3, simple case
client = Client(ClientConfig.from_url("https://api.example.com", token))

# v3, when you need to set other options
client = Client(ClientConfig(
    url="https://api.example.com",
    token=token,
    timeout=Timeout(connect=5.0, read=30.0),
))
```

`ClientConfig.from_url()` exists precisely so the common case stays a one-liner. Reach for the full constructor only when you're configuring timeouts, retries, or logging hooks.

If you construct clients in many places, this is a good moment to centralise: build the config once and pass it around, rather than repeating `from_url` at every call site.

### 2. Return types

Every method that returned a `dict` now returns a typed dataclass. Key access becomes attribute access.

```python
# v2
result = client.get_page(1)
for item in result["items"]:
    print(item["name"])

# v3
result = client.get_page(1)
for item in result.items:
    print(item.name)
```

**This is the change to be most careful about.** v2.9 cannot warn on it — the objects it returns really are dicts, so there's nothing to deprecate. Expect `TypeError: 'Page' object is not subscriptable` at runtime after you upgrade, in code paths your tests don't cover.

A few things that help:

- **Grep for subscripting on results.** Search for patterns like `result[`, `response[`, `.get(` on anything returned by the client.
- **Watch for `.get()` with defaults.** `result.get("items", [])` has no direct equivalent; the dataclass field either exists or the attribute access fails at import-time type-check. Use `getattr(result, "items", [])` only if you genuinely have version-straddling code — otherwise just access the field.
- **Serialization breaks silently.** `json.dumps(result)` worked in v2 and raises in v3. If you were passing results straight to a JSON response or a cache, use `dataclasses.asdict(result)`.
- **Run a type checker.** This is the one change where mypy or pyright will find call sites your tests miss. If you're not already running one, adding it for this migration pays for itself.

### 3. `fetch_all()` is removed

`Client.fetch_all()` loaded the entire result set into memory. It's gone. Use `Client.iterate()`, which yields pages.

```python
# v2
items = client.fetch_all()
for item in items:
    process(item)

# v3
for page in client.iterate():
    for item in page.items:
        process(item)
```

Note that `iterate()` yields **pages**, not individual items — the nested loop is intentional. If you want a flat stream:

```python
from itertools import chain

for item in chain.from_iterable(page.items for page in client.iterate()):
    process(item)
```

If some code genuinely needs the whole set in memory (say, to sort it), you can still materialise it explicitly — but now the memory cost is visible at the call site rather than hidden in the library:

```python
items = [item for page in client.iterate() for item in page.items]
```

Be honest about which of your `fetch_all()` calls actually needed everything at once. Most don't, and streaming is the point of the change.

### 4. Timeouts

Timeouts are now a `Timeout` object with separate `connect` and `read` values. **Passing a float raises `TypeError` rather than warning** — this is a hard failure in v3, though v2.9 will warn you about it first.

```python
# v2
client = Client(url, token, timeout=30.0)

# v3
client = Client(ClientConfig(
    url=url,
    token=token,
    timeout=Timeout(connect=5.0, read=30.0),
))
```

The old single float conflated two very different things. When splitting an existing value, the usual translation is a short `connect` (a few seconds — either the TCP handshake succeeds quickly or the host is unreachable) and your old value as `read`. Don't set `connect` to your old 30-second timeout; you'll wait 30 seconds to discover a bad hostname.

### 5. Python 3.10 minimum

Python 3.8 is no longer supported. Update your CI matrix, `pyproject.toml` (`requires-python = ">=3.10"`), and any container base images before upgrading. If you're pinning transitively through another package, check that it also supports 3.10+.

---

## New in v3 (nothing to migrate)

These are additions — you can adopt them after the migration, not during it. Resist the temptation to do both at once; a migration that only removes breakage is much easier to review and revert.

- **`AsyncClient`** — the same API, `async`/`await`. `AsyncClient.iterate()` is an async generator, so `async for page in client.iterate()`.
- **Automatic retry on 429**, honouring `Retry-After`. If you wrote your own rate-limit backoff around v2, you can likely delete it — and you should check that it isn't now stacking on top of the built-in retry, which would multiply your wait times.
- **Structured logging hooks**, configurable on `ClientConfig`. Useful for wiring request/response metadata into your existing observability setup.

---

## Migration checklist

- [ ] Interpreter is Python 3.10+; CI matrix and packaging metadata updated
- [ ] Upgraded to v2.9, test suite run with `-W error::DeprecationWarning`, all warnings fixed
- [ ] Every `Client(...)` call site uses `ClientConfig` / `ClientConfig.from_url`
- [ ] Every float timeout replaced with `Timeout(connect=..., read=...)`
- [ ] Every `fetch_all()` call replaced with `iterate()`, with the nested page loop
- [ ] Dict-style access on results converted to attribute access
- [ ] `json.dumps` / caching of result objects switched to `dataclasses.asdict`
- [ ] Type checker run against the codebase (catches what tests miss)
- [ ] Upgraded to v3, full test suite green
- [ ] Any hand-rolled 429 backoff removed or checked for double-retry