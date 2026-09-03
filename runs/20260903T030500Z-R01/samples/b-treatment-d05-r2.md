# Migrating from v2 to v3

## Before you start

v3 requires Python 3.10. If you're on 3.8, upgrade the interpreter first — everything below assumes you're already running a supported version.

The maintainers recommend a two-step upgrade. Move to v2.9 first, which emits `DeprecationWarning` for every change listed here. Run your test suite with `-W error::DeprecationWarning` to turn those warnings into failures, fix them all, then bump to v3. There's no codemod; the warnings are the closest thing to one. Going straight to v3 works, but you'll be debugging `TypeError`s instead of reading warnings that tell you what to change.

## Client construction

The two-positional-arg constructor is gone.

```python
# v2
client = Client("https://api.example.com", "token-abc")

# v3
client = Client(ClientConfig.from_url("https://api.example.com", "token-abc"))
```

`ClientConfig.from_url` covers the simple case. Build `ClientConfig` directly when you need to set timeouts, retries, or logging hooks.

## Return types

Methods that returned `dict` now return dataclasses. Key access becomes attribute access:

```python
# v2
result["items"]
result["page"]["next"]

# v3
result.items
result.page.next
```

Two consequences worth checking for. Code that iterated over keys, called `.get()` with a default, or passed results to `json.dumps` needs rework — use `dataclasses.asdict()` where you genuinely need a dict. And typos now fail loudly: `result.itmes` raises `AttributeError` where `result["itmes"]` raised `KeyError`, which is the same class of bug but may surface in different places if you were catching `KeyError` broadly.

## `fetch_all()` is removed

It buffered the entire result set in memory. Use `iterate()`, which yields pages:

```python
# v2
for item in client.fetch_all():
    process(item)

# v3
for page in client.iterate():
    for item in page.items:
        process(item)
```

If you truly need everything in memory — a small, bounded result set — write it explicitly:

```python
items = [item for page in client.iterate() for item in page.items]
```

Doing it by hand is the point: it's now visible in review when someone loads an unbounded set into a list.

## Timeouts

Floats are rejected outright. In v2.9 a float warns; in v3 it raises `TypeError`.

```python
# v2
client.fetch(timeout=30.0)

# v3
client.fetch(timeout=Timeout(connect=5.0, read=30.0))
```

There's no automatic translation, because the old float was ambiguous about which phase it bounded. Pick connect and read values deliberately rather than mapping your old number to both — a 30-second connect timeout is rarely what you want.

## New in v3

None of these require changes, but they may let you delete code:

- **`AsyncClient`** — same API surface, `async`/`await`. `iterate()` becomes an async generator.
- **Automatic retry on 429**, honouring `Retry-After`. If you wrapped calls in your own rate-limit backoff, that's now redundant and may compound with the built-in retry. Check for it.
- **Structured logging hooks**, configured on `ClientConfig`.

## Suggested order

1. Upgrade to Python 3.10+.
2. Pin v2.9, run tests with deprecation warnings as errors.
3. Fix construction, then return types, then `fetch_all`, then timeouts — roughly increasing order of how much code each touches.
4. Remove any hand-rolled 429 backoff.
5. Bump to v3.