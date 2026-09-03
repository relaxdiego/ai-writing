# Migrating from v2 to v3

v3 changes five things that will break existing code: client construction, return types, bulk fetching, timeouts, and the minimum Python version. There is no codemod. The recommended path is to upgrade to v2.9 first, fix every deprecation warning it emits, and only then move to v3 — at that point the jump should be a version bump and nothing else.

## Recommended path

```
pip install 'yourlib>=2.9,<3'
python -W error::DeprecationWarning -m pytest    # or your normal test command
```

v2.9 warns about all five changes below. Turning warnings into errors makes them impossible to miss, and everything v2.9 warns about is still functional, so you can fix call sites incrementally on a working codebase. Once the suite is clean:

```
pip install 'yourlib>=3,<4'
```

If you skip v2.9, expect the failures to surface as `TypeError` and `AttributeError` at runtime rather than as warnings.

## Python 3.10 minimum

Do this first — it gates everything else. v3 drops 3.8 and 3.9. If you are on 3.8, upgrade the interpreter before touching library code, or you will be debugging two migrations at once.

## Client construction

`Client(url, token)` is replaced by `Client(config: ClientConfig)`.

```python
# v2
client = Client("https://api.example.com", token)

# v3
client = Client(ClientConfig.from_url("https://api.example.com", token))
```

`ClientConfig.from_url` covers the simple case and is the direct translation. Construct `ClientConfig` directly when you need to set anything else — timeouts, retry behaviour, logging hooks.

## Typed return values

Methods that returned `dict` now return dataclasses. Key access becomes attribute access.

```python
# v2
result = client.get_page(1)
items = result["items"]
cursor = result["next_cursor"]

# v3
result = client.get_page(1)
items = result.items
cursor = result.next_cursor
```

Two things to watch for beyond the mechanical rewrite:

- **`.get()` with a default no longer works.** `result.get("next_cursor")` returned `None` for a missing key; the dataclass field is always present, so check the value instead (`if result.next_cursor is not None`). Where you relied on a key being absent to mean something, that distinction is now carried by the field's value.
- **Serialisation changes.** `json.dumps(result)` fails on a dataclass. Use `dataclasses.asdict(result)`, or whatever serialisation helper the library exposes, before writing to disk or sending over the wire. If you persist these structures anywhere, check the resulting shape against what you stored under v2.

## `fetch_all()` is removed

`fetch_all()` loaded the whole result set into memory. `iterate()` yields pages instead.

```python
# v2
for item in client.fetch_all():
    process(item)

# v3
for page in client.iterate():
    for item in page.items:
        process(item)
```

Note the extra level: `iterate()` yields *pages*, not items. If you want a flat item stream, wrap it once:

```python
def all_items(client):
    for page in client.iterate():
        yield from page.items
```

Code that genuinely needs the full set in memory — sorting across the whole result, taking a length, indexing — can do `items = [i for page in client.iterate() for i in page.items]`, but that reintroduces the memory cost `fetch_all()` was removed for. Prefer streaming where the work is per-item.

## Timeouts

A float is no longer accepted, and in v3 passing one raises `TypeError` rather than warning.

```python
# v2
client = Client(url, token, timeout=30.0)

# v3
config = ClientConfig.from_url(url, token)
config.timeout = Timeout(connect=5.0, read=30.0)
client = Client(config)
```

The old single float applied to the whole operation, so there is no exactly equivalent translation. A reasonable default is a short `connect` (a few seconds — connection setup either succeeds quickly or is not going to) and your previous value for `read`. Be aware that the new total worst case is `connect + read`, slightly longer than the old bound; if you have an outer deadline that depended on the old value, adjust it.

## Additions (optional)

None of these are required to complete the migration, but they may let you delete code you currently maintain by hand:

- **`AsyncClient`** — same surface as `Client` with awaitable methods; `iterate()` becomes an async generator.
- **Automatic retry on 429**, honouring `Retry-After`. If you have hand-rolled rate-limit backoff wrapped around client calls, it is now redundant and may compound with the built-in retry. Remove it or disable the built-in.
- **Structured logging hooks**, configured on `ClientConfig`. Useful replacement for logging wrappers around call sites.

## Checklist

1. Move to Python 3.10+.
2. Pin to `>=2.9,<3`, run tests with `DeprecationWarning` as an error.
3. Rewrite `Client(...)` construction to use `ClientConfig`.
4. Convert `result["key"]` to `result.key`; fix `.get()` calls and any serialisation.
5. Replace `fetch_all()` with `iterate()`, adding the page loop.
6. Replace float timeouts with `Timeout(connect=..., read=...)`.
7. Remove hand-rolled 429 retry logic if you have it.
8. Warnings clean → bump to `>=3,<4`.