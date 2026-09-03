# Migrating from v2 to v3

Upgrade in two steps: move to v2.9 first, fix everything it warns about, and only then install v3. Every breaking change below emits a `DeprecationWarning` in v2.9, so the intermediate release turns a silent set of runtime failures into a list you can work through with the old library still running. Going straight to v3 means discovering the same list one traceback at a time.

To make the warnings impossible to miss, run your test suite with them promoted to errors:

```
python -W error::DeprecationWarning -m pytest
```

There is no codemod. The changes are mechanical but not textually regular, so the sections below give the before-and-after for each one.

## Client construction takes a config object

`Client(url, token)` is replaced by `Client(config)`. For the common case where you have only a URL and a token, `ClientConfig.from_url` covers it:

```python
# v2
client = Client("https://api.example.com", "tok_123")

# v3
client = Client(ClientConfig.from_url("https://api.example.com", "tok_123"))
```

If you construct clients in more than a couple of places, build the config once and pass it around; that is the arrangement the new signature is designed for, and it is where the change stops being pure overhead.

## Responses are dataclasses, not dicts

Methods that returned `dict` now return typed dataclasses, so key access becomes attribute access:

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

Two consequences are worth checking for deliberately, because neither shows up as a `TypeError` at the call site. Code that treated responses as plain data — `json.dumps(result)`, `result.get("items", [])`, `**result` splats, `"items" in result` — needs rewriting rather than a mechanical `[]`-to-`.` substitution. And keys that were optional in v2 are now fields that are always present, typically defaulting to `None`, so a `.get()` with a fallback becomes an explicit `is None` check.

## `fetch_all()` is gone; `iterate()` yields pages

`fetch_all()` was removed because it materialised the entire result set. The replacement yields pages, not items, which is the detail that most often gets missed:

```python
# v2
for item in client.fetch_all():
    process(item)

# v3
for page in client.iterate():
    for item in page.items:
        process(item)
```

If you would rather keep a flat loop, `itertools.chain.from_iterable(page.items for page in client.iterate())` gives you one lazily. What you should not do is reach for `list(client.iterate())` to preserve the old shape: that reintroduces exactly the memory behaviour the removal was meant to fix, and it does so silently until the day a result set is large enough to matter.

## Timeouts are `Timeout` objects

Floats are no longer accepted. Passing one raises `TypeError` in v3 rather than warning, so any timeout you miss in the v2.9 pass will fail at the call:

```python
# v2
client.get_page(1, timeout=30.0)

# v3
client.get_page(1, timeout=Timeout(connect=5.0, read=30.0))
```

There is no automatic split of an old float into the two new values, and the sensible split is usually not even: a connect timeout wants to be short, a read timeout wants to accommodate the slowest response you are willing to wait for. Treat each site as a decision rather than a substitution.

## Python 3.10 is the minimum

Support for 3.8 is dropped and the floor is 3.10, so 3.9 users are affected too. Do this bump after fixing the v2.9 warnings but before installing v3 — v2.9 still runs on the older interpreters, which lets you separate a library migration from an interpreter migration instead of debugging both at once. Update your CI matrix and any `python_requires` or `requires-python` metadata at the same time.

## What you get in v3

Nothing here requires changes to working code. `AsyncClient` mirrors the synchronous API for `async`/`await` callers. Requests that receive a 429 are retried automatically with the `Retry-After` header honoured, which may let you delete hand-rolled backoff logic — worth grepping for, since a retry loop wrapped around a client that now retries internally will multiply the wait. Structured logging hooks replace whatever you were doing with the standard logging module to get request-level detail.

One caveat on the code above: the field and parameter names in the examples follow the change list rather than the shipped signatures. Check `Timeout`'s keyword names and the dataclass field names against the v3 API reference before running a bulk find-and-replace across your codebase.