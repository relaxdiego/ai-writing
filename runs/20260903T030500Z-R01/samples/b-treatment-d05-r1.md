# Migrating from v2 to v3

## Upgrade path

There's no codemod. Upgrade in two steps:

1. Move to **v2.9**. Every breaking change below emits a deprecation warning there. Run your test suite with `-W error::DeprecationWarning` to surface them all, and fix them under v2.9 where both old and new APIs work.
2. Move to **v3** once the warnings are gone.

Before starting, confirm you're on **Python 3.10 or later**. 3.8 support is dropped; this is the one thing v2.9 can warn about but not smooth over.

## Breaking changes

### Client construction

`Client(url, token)` is replaced by `Client(config: ClientConfig)`.

```python
# v2
client = Client("https://api.example.com", token)

# v3
client = Client(ClientConfig.from_url("https://api.example.com", token))
```

`ClientConfig.from_url` covers the two-argument case. Construct `ClientConfig` directly when you need to set anything else.

### Return types

Methods that returned `dict` now return dataclasses. Key access becomes attribute access:

```python
# v2
for item in result["items"]:
    print(item["name"])

# v3
for item in result.items:
    print(item.name)
```

Watch for indirect key access — `result.get("items", [])`, `**result` splats, `json.dumps(result)`, and anything that iterates keys. These won't be caught by a search for `result["`. `dataclasses.asdict()` gets you back to a plain dict if you need one at a serialization boundary.

### `fetch_all()` removed

`fetch_all()` loaded the entire result set into memory. Use `iterate()`, which yields pages:

```python
# v2
items = client.fetch_all()

# v3
items = [item for page in client.iterate() for item in page]
```

That flattening reproduces the old behaviour, memory cost included. If you were streaming or filtering, work page by page instead.

### Timeouts

Floats are gone. Pass a `Timeout` with separate connect and read values:

```python
# v2
client.request(..., timeout=5.0)

# v3
client.request(..., timeout=Timeout(connect=2.0, read=5.0))
```

In v3 a float raises `TypeError` — it does not warn. If your timeouts come from config files or environment variables, the failure surfaces at runtime rather than at import, so check those paths explicitly.

## New in v3

- **`AsyncClient`** — same surface as `Client`, awaitable. Adopt incrementally; the sync client isn't deprecated.
- **Automatic retry on 429**, honouring `Retry-After`. If you have hand-rolled 429 retry logic, remove it to avoid compounding backoff.
- **Structured logging hooks** for request/response instrumentation.