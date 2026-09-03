# Migrating from v2 to v3

## Upgrade in two steps

There is no codemod for this release, so the practical path runs through v2.9 rather than jumping straight to v3. Version 2.9 is API-compatible with the rest of the 2.x line but emits a `DeprecationWarning` for every construct that v3 removes or changes, which turns a large blind refactor into a list of concrete file-and-line locations. Pin to `2.9`, run your test suite with warnings made visible, and work through what it reports:

```bash
pip install 'yourlib>=2.9,<3'
python -W error::DeprecationWarning -m pytest
```

Promoting the warnings to errors is the aggressive version and is worth it if your suite has decent coverage, since it forces each call site to be fixed rather than logged and forgotten. If the suite is thin, run with plain `-W default::DeprecationWarning` first, collect the unique warning sites, and fix them in batches. Once a run under `-W error::DeprecationWarning` is clean, the move to v3 should be close to a version bump.

## Breaking changes

### Client construction takes a config object

`Client(url, token)` is gone in favour of a single `ClientConfig` argument, which gives new options somewhere to live without growing the positional signature further. For call sites that only ever passed a URL and a token, the `from_url` helper is a direct translation and is the right choice unless you need the other fields:

```python
# v2
client = Client("https://api.example.com", "tok_123")

# v3
client = Client(ClientConfig.from_url("https://api.example.com", "tok_123"))

# v3, when you need more than the simple case
client = Client(ClientConfig(
    base_url="https://api.example.com",
    token="tok_123",
    timeout=Timeout(connect=5.0, read=30.0),
))
```

### Methods return dataclasses, not dicts

Every method that used to hand back a `dict` now returns a typed dataclass, so key access becomes attribute access: `result["items"]` becomes `result.items`, and `result["page"]["next"]` becomes `result.page.next`. The change buys you static checking and editor completion on response shapes, and it also means typos fail loudly at the access rather than surfacing as a `KeyError` several frames later. The cost is that code treating responses as generic mappings — `.get()` with a default, `in` checks, `**result` splats, iteration over keys, `json.dumps(result)` — no longer works and has to be rewritten. For serialization specifically, use `dataclasses.asdict(result)`, and for optional fields prefer `getattr(result, "field", None)` only where the field is genuinely conditional; in most cases the dataclass declares it with a default and plain attribute access is correct.

### `fetch_all()` is removed

`Client.fetch_all()` materialized the entire result set in memory, which was fine for small collections and a reliable source of production incidents for large ones. `Client.iterate()` replaces it by yielding pages, letting you process results incrementally and stop early:

```python
# v2
for item in client.fetch_all(query):
    process(item)

# v3
for page in client.iterate(query):
    for item in page.items:
        process(item)
```

If some call site genuinely needs everything in memory — a small, bounded lookup table, say — the replacement is a one-liner, `items = [i for page in client.iterate(query) for i in page.items]`, but write it deliberately rather than reflexively, because the reason `fetch_all` was removed is that it made the unbounded case invisible at the call site.

### Timeouts are objects, not floats

Timeouts now take a `Timeout` instance carrying separate `connect` and `read` values, so a slow-to-establish connection and a slow-to-respond endpoint can be tuned independently. Passing a bare float raises `TypeError` rather than warning, and this is deliberate: silently reinterpreting an old scalar as one of the two new values would produce a timeout budget nobody asked for. Translate a v2 float by deciding which half it was really protecting; `Timeout(connect=5.0, read=old_value)` preserves the old read behaviour for most code, since the previous scalar was applied to the whole request and read time dominates in practice.

### Python 3.8 is no longer supported

The minimum is now 3.10. If you are still on 3.8, upgrade the interpreter before starting the library migration rather than alongside it, so that failures during the v3 move are attributable to one change and not two.

## What you get in return

Version 3 adds an `AsyncClient` with the same surface as the synchronous client, so `await client.iterate(query)` and the rest work under `asyncio` without a separate wrapper layer. Rate limiting is now handled for you: a 429 response triggers an automatic retry that honours the `Retry-After` header, which replaces most hand-rolled backoff loops built against v2. Structured logging hooks let you attach request and response records to your own logger with the fields already separated, instead of parsing them back out of formatted strings. None of these require changes to existing code — they are available once you are on v3, and adopting them can happen well after the migration lands.