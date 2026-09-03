# Migrating from v2 to v3

Do the upgrade in two hops: move to v2.9 first, clear every deprecation warning it emits, and only then pin v3. Every breaking change below has a corresponding warning in 2.9, so the intermediate release turns what would be a wall of import-time and call-time failures into a list of warnings you can work through while your test suite still passes. There is no codemod, and the dataclass migration in particular touches call sites that a regex cannot find safely, so the warnings are the closest thing to a mechanical checklist you will get.

| Area | v2 | v3 |
| --- | --- | --- |
| Construction | `Client(url, token)` | `Client(ClientConfig.from_url(url, token))` |
| Return values | `result["items"]` | `result.items` |
| Full result set | `client.fetch_all()` | `for page in client.iterate():` |
| Timeouts | `timeout=5.0` | `timeout=Timeout(connect=2.0, read=5.0)` |
| Python | 3.8+ | 3.10+ |

## Before you start: Python 3.10

v3 drops Python 3.8 and requires 3.10 or newer. This gates everything else, so settle it first: if part of your fleet is still on 3.8 or 3.9, the interpreter upgrade is its own project and v2.9 will keep running on 3.8 while you do it. Bump `requires-python` in your own package metadata at the same time, otherwise pip will happily resolve v3 for a downstream user on 3.9 and fail at import.

## Client construction

The two positional arguments are gone in favour of a single config object. For the common case, `ClientConfig.from_url` reproduces the old call exactly:

```python
# v2
client = Client("https://api.example.com", "token-abc")

# v3
from yourlib import Client, ClientConfig

client = Client(ClientConfig.from_url("https://api.example.com", "token-abc"))
```

If you were passing keyword arguments to `Client` beyond the URL and token, those move onto `ClientConfig` as fields rather than staying on the constructor. Construct the config directly in that case instead of routing through the helper. The config object is also the thing worth hoisting into your application settings: it is inspectable and comparable, so a single `ClientConfig` can be built once at startup and handed to both a sync and an async client.

## Dict returns become dataclasses

Every method that returned a `dict` now returns a typed dataclass, and key access becomes attribute access:

```python
# v2
result = client.search("widgets")
for item in result["items"]:
    print(item["name"])

# v3
result = client.search("widgets")
for item in result.items:
    print(item.name)
```

The subscript is the obvious break and it fails loudly, since subscripting a dataclass raises `TypeError`. The quieter breaks are the rest of the mapping protocol you may have been leaning on without noticing. `result.get("items", [])` has no equivalent and should become a plain attribute read, because a field that can be absent is now typed as `None` rather than missing. `"items" in result` no longer does what it looks like. Anything that iterated the response as a mapping, or passed it straight to `json.dumps`, needs `dataclasses.asdict(result)` in between. Grep for `json.dumps`, `.get(`, `in result` and `**result` around your call sites, not just for square brackets.

The upside is that your type checker now sees the response shape. If you were maintaining hand-written `TypedDict`s to describe v2 responses, delete them.

## `fetch_all()` is removed

`fetch_all()` loaded the entire result set into memory, which is why it is gone rather than deprecated in place. `iterate()` yields pages, so the replacement is a nested loop:

```python
# v2
for item in client.fetch_all():
    process(item)

# v3
for page in client.iterate():
    for item in page.items:
        process(item)
```

If a piece of code genuinely needs the whole set materialised, such as sorting across pages or taking a length, you can flatten it explicitly:

```python
items = [item for page in client.iterate() for item in page.items]
```

Write that only where you have thought about the size of the result. It reintroduces exactly the memory profile v3 removed, and the explicit comprehension at least makes the cost visible at the call site rather than hiding it behind a method name.

## Timeouts

Timeouts are now a `Timeout` object with separate connect and read values. Passing a float raises `TypeError` and there is no compatibility shim in v3, though v2.9 will warn:

```python
# v2
client.get("/items", timeout=5.0)

# v3
from yourlib import Timeout

client.get("/items", timeout=Timeout(connect=2.0, read=5.0))
```

There is no mechanical translation from your old float, because a single value could not distinguish a server that refuses to accept the connection from one that accepts and then stalls. `Timeout(connect=old, read=old)` preserves the old worst-case behaviour and is the safe literal port. The more useful setting is a short connect timeout, a second or two, with the read timeout carrying whatever latency budget the endpoint actually needs. Do that as a follow-up once the migration is green, not during it.

## Clearing the warnings on 2.9

Pin `>=2.9,<3` and run your suite with deprecation warnings promoted to errors so nothing hides in a code path your eyes skip:

```bash
python -W error::DeprecationWarning -m pytest
```

Or, in `pyproject.toml`, scoped to this library so you are not signing up to fix the rest of your dependency tree at the same time:

```toml
[tool.pytest.ini_options]
filterwarnings = ["error:::yourlib.*"]
```

Test coverage is the limit of this technique. A warning only fires on a line that runs, so a rarely-exercised error handler that reads `result["error"]` will stay silent through the whole 2.9 pass and then fail in production under v3. Where coverage is thin, the grep for dict-style access is doing the real work, and the warnings are the confirmation.

## What you get in v3

Once the pin lands, three additions are available and none of them require further changes to migrated code. `AsyncClient` mirrors the sync API and takes the same `ClientConfig`, so an async call site is the same code with `await` and `async for`. Retries on HTTP 429 are automatic and honour `Retry-After`, which means any hand-rolled backoff you wrapped around v2 calls is now redundant and should come out; leaving it in place gives you two layers of backoff multiplying each other. Structured logging hooks let you attach request and response records to your own logger instead of parsing the library's log lines, which is the natural place to move any instrumentation that was previously reading the dicts you just converted to dataclasses.