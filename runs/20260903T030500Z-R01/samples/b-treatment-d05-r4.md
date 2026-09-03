# Migrating from v2 to v3

## Before you start

v3 requires Python 3.10 or later. If you're on 3.8, resolve that first — the rest of this guide assumes a supported interpreter.

The maintainers recommend a two-step upgrade. Pin to v2.9 first, which emits `DeprecationWarning` for every breaking change below. Run your test suite with `-W error::DeprecationWarning` to turn those warnings into failures, fix them all, and only then move to v3. This works because v2.9 accepts both the old and new forms of every API. There is no codemod; the changes are mechanical but require judgment about types and memory behaviour.

## Client construction

`Client(url, token)` no longer accepts positional arguments. It takes a single `ClientConfig`:

```python
# v2
client = Client("https://api.example.com", "tok_123")

# v3
client = Client(ClientConfig.from_url("https://api.example.com", "tok_123"))
```

`ClientConfig.from_url` covers the simple case. Construct `ClientConfig` directly when you need to set timeouts, retry behaviour, or logging hooks.

## Return types

Methods that returned `dict` now return dataclasses. Key access becomes attribute access:

```python
# v2
result["items"]
result.get("next_cursor")

# v3
result.items
result.next_cursor
```

Two things to watch. `.get()` with a default has no direct equivalent — fields that may be absent are typed `Optional` and default to `None`, so check for `None` instead of supplying a fallback key. And code that treated responses as plain dicts — passing them to `json.dumps`, iterating `.keys()`, merging with `**` — needs updating. `dataclasses.asdict()` gets you back to a dict where you genuinely need one.

This change is worth the disruption if you run a type checker: mistyped field names are now caught statically rather than at runtime.

## `fetch_all()` is removed

`fetch_all()` loaded the entire result set into memory. Use `iterate()`, which yields pages:

```python
# v2
for item in client.fetch_all():
    process(item)

# v3
for page in client.iterate():
    for item in page.items:
        process(item)
```

Note the extra loop level — `iterate()` yields pages, not items. If you need a flat stream, `itertools.chain.from_iterable(page.items for page in client.iterate())` does it.

Code that relied on getting a list back (indexing, `len()`, multiple passes) needs restructuring. Calling `list()` on the iterator reproduces the old behaviour and the old memory profile; do it only when the result set is known to be small.

## Timeouts

Timeouts are now a `Timeout` object with separate connect and read values. Passing a float raises `TypeError` — it does not warn, and it does not coerce.

```python
# v2
client.fetch(timeout=30.0)

# v3
client.fetch(timeout=Timeout(connect=5.0, read=30.0))
```

The old float applied to the whole operation, so there's no exact translation. Using it as the read timeout with a short connect timeout is the usual choice.

## What you get in v3

None of these require changes, but they may let you delete code:

- **`AsyncClient`** — mirrors `Client` with `async`/`await`. `iterate()` becomes an async generator.
- **Automatic retry on 429**, honouring `Retry-After`. If you wrote your own rate-limit backoff, it's now redundant and may interfere.
- **Structured logging hooks**, configured through `ClientConfig`.

## Suggested order

1. Upgrade to Python 3.10+.
2. Pin v2.9, run tests with deprecation warnings as errors.
3. Fix construction, return types, and pagination — these are the bulk of the work.
4. Fix timeouts, which v2.9 warns about but v3 rejects outright.
5. Move to v3 and remove any hand-rolled 429 handling.