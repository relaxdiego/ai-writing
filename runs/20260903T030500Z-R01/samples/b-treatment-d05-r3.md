# Migrating from v2 to v3

## Before you start

v3 requires Python 3.10 or later. If you're on 3.8, upgrade the interpreter first — none of the rest of this guide applies until you do.

There is no codemod. The recommended path is to install v2.9 first, which emits `DeprecationWarning` for every change described below, fix your code until the warnings are gone, and only then move to v3. Run your test suite with `-W error::DeprecationWarning` to make the warnings fail loudly instead of scrolling past.

## Client construction

The two-argument constructor is gone.

```python
# v2
client = Client("https://api.example.com", token)

# v3
client = Client(ClientConfig.from_url("https://api.example.com", token))
```

`from_url` covers the simple case. If you were passing other options to the constructor, build a `ClientConfig` directly instead.

## Return types

Methods that returned `dict` now return dataclasses, so key access becomes attribute access:

```python
# v2
result["items"]
result["page"]["next"]

# v3
result.items
result.page.next
```

Code that treated results as generic mappings needs more than a mechanical edit. `result.get("items", [])`, `**result`, `json.dumps(result)`, and iteration over keys all stop working. Dataclasses give you `dataclasses.asdict()` if you genuinely need a dict — for serialisation boundaries, say — but prefer reading the attributes you want.

## `fetch_all()` is removed

`fetch_all()` materialised the entire result set. Use `iterate()`, which yields one page at a time:

```python
# v2
for item in client.fetch_all():
    process(item)

# v3
for page in client.iterate():
    for item in page.items:
        process(item)
```

Note the extra loop: `iterate()` yields pages, not items. If you need the old flattened behaviour and are confident the result set fits in memory, `itertools.chain.from_iterable(p.items for p in client.iterate())` gives you an item iterator — though the reason `fetch_all()` was removed is that this assumption tends to be wrong in production.

## Timeouts

Floats are no longer accepted, and passing one raises `TypeError` rather than warning:

```python
# v2
client.fetch(timeout=30.0)

# v3
client.fetch(timeout=Timeout(connect=5.0, read=30.0))
```

Splitting connect from read means you have to decide what the old single number meant. A conservative translation is to keep your old value as `read` and set a short `connect` — a connection that hasn't established in a few seconds usually isn't going to.

## After upgrading

Three additions you may want, none of which require changes to work:

- **`AsyncClient`** — same API surface, `await`ed. Useful if you were wrapping the sync client in a thread pool.
- **Automatic retry on 429**, honouring `Retry-After`. If you built your own rate-limit backoff around v2, you can likely delete it; check that it isn't now retrying on top of the built-in retry.
- **Structured logging hooks**, for wiring request/response events into your logging setup.