# Migrating from v2 to v3

## Go through v2.9 first

There is no codemod for this upgrade, so the deprecation warnings in v2.9 are the closest thing to one. Pin to 2.9, run your test suite with `-W error::DeprecationWarning`, and fix what it flags; every breaking change described below emits a warning there under the old API, which means a codebase that runs clean on 2.9 will usually run clean on 3.0 without further edits. Going straight from 2.x to 3.0 works too, but you trade a list of warnings pointing at exact call sites for a series of `TypeError`s and `AttributeError`s discovered one test run at a time.

The one change 2.9 cannot warn you about is the Python version, so settle that first.

## Python 3.10 is now the minimum

Support for 3.8 is dropped and 3.9 is not supported either; v3 requires 3.10 or later. If you are still on 3.8, do that interpreter upgrade as its own change, with its own test run, before you touch any library code. Debugging a `match` statement's absence and a changed constructor signature in the same pull request is unpleasant.

## `Client` takes a config object

The constructor no longer accepts a URL and token as positional arguments. It takes a single `ClientConfig`, and for the common case there is a helper that reproduces the old call exactly:

```python
# v2
client = Client("https://api.example.com", token)

# v3
client = Client(ClientConfig.from_url("https://api.example.com", token))
```

If you were passing extra keyword arguments to the constructor, they now belong on the config object instead, either as arguments to `ClientConfig(...)` directly or set on the instance returned by `from_url`. This is worth a moment's thought rather than a mechanical rewrite: if you construct clients in several places with slightly different options, a config object is a thing you can build once, store, and pass around, which is largely why the signature changed.

## Methods return dataclasses, not dicts

Every method that used to hand back a `dict` now returns a typed dataclass, and key access becomes attribute access:

```python
# v2
items = result["items"]
cursor = result.get("next_cursor")

# v3
items = result.items
cursor = result.next_cursor
```

The subscript form is the obvious breakage and the one the warnings will catch, but the incidental dict behaviours are what tend to survive the first pass and fail later. Anything that called `.get()` with a default, tested membership with `in`, iterated `.keys()` or `.items()`, splatted a result into a function with `**result`, or passed one straight to `json.dumps` needs rewriting. For serialisation, `dataclasses.asdict(result)` gives you the dict back. For an optional field, read the attribute and compare against `None` rather than reaching for a default, since the field is always present on the dataclass even when its value is missing.

## `fetch_all()` is gone; use `iterate()`

`fetch_all()` was removed rather than deprecated in place because its whole behaviour was the problem: it accumulated every page in memory before returning. `iterate()` yields pages instead, so the rewrite is a loop with one extra level of nesting:

```python
# v2
for item in client.fetch_all():
    handle(item)

# v3
for page in client.iterate():
    for item in page.items:
        handle(item)
```

Where the surrounding code genuinely needs the whole collection in memory, say because it sorts or counts across the full set, you can write `list(chain.from_iterable(page.items for page in client.iterate()))`. Do that knowingly, though, since it reintroduces exactly the memory profile the removal was meant to eliminate. Code that only streams through results should stay streaming.

## Timeouts are a `Timeout` object

A float is no longer accepted and no longer coerced; passing one raises `TypeError` at the call site. Connect and read timeouts are now separate values:

```python
# v2
client.request(..., timeout=30.0)

# v3
client.request(..., timeout=Timeout(connect=5.0, read=30.0))
```

Splitting one number into two is a judgment call, not a substitution, because the old float bounded the whole operation while the new values bound two different phases. A short connect timeout and a longer read timeout is the usual shape: failing to establish a connection is nearly always a fast, permanent failure, whereas a slow response is often a slow success. Carrying your old value over as the read timeout and choosing something small for connect will preserve behaviour closely enough for most callers.

## What you get in return

`AsyncClient` mirrors the synchronous API with the same config object and the same return types, so the migration to async, if you want it, is mostly a matter of awaiting calls and writing `async for page in client.iterate()`. Rate limiting is now handled for you: v3 retries automatically on a 429 and honours the `Retry-After` header. Check whether you have your own 429 handling, because retry loops compose badly, and a hand-written backoff wrapped around a client that already backs off will wait far longer than either layer intends. Removing yours is usually the right move. Finally, structured logging hooks let you attach a handler that receives request and response records as objects rather than formatted strings, which is worth wiring up while you are already touching client construction.