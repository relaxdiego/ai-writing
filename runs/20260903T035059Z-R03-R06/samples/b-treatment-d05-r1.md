# Migrating from v2 to v3

There is no codemod for this release, and the changes touch nearly every call site, so the maintainers recommend upgrading in two passes. Move first to v2.9, which is API-compatible with the rest of the v2 line but emits a `DeprecationWarning` for every construct v3 removes. Run your test suite with `-W error::DeprecationWarning` so the warnings fail loudly rather than scrolling past, fix each one against the still-working v2 API, and only then bump to v3. A codebase that runs clean under v2.9 with warnings as errors will generally import and run under v3 unchanged.

## Python version

The minimum supported version is now 3.10; 3.8 support is dropped and 3.9 was never supported. Do this first, because the rest of the migration is easier to reason about once you are on an interpreter that can express the new type signatures. If you are pinned to 3.8 by a dependency, resolve that before starting, since v2.9 still installs on 3.8 and will let you postpone the problem to the point where you have no working version to fall back to.

## Constructing a client

`Client(url, token)` is replaced by `Client(config: ClientConfig)`. For the common case where you have nothing but a URL and a token, the helper reproduces the old behaviour:

```python
# v2
client = Client("https://api.example.com", token)

# v3
client = Client(ClientConfig.from_url("https://api.example.com", token))
```

Where you were passing extra keyword arguments to the constructor, build the `ClientConfig` explicitly instead and set the fields there. The indirection buys you a config object you can construct once, validate, and reuse across clients, which is also what `AsyncClient` accepts.

## Dictionaries became dataclasses

Every method that returned a `dict` now returns a typed dataclass, so key access becomes attribute access: `result["items"]` is `result.items`, and `result["page"]["next"]` is `result.page.next`. The mechanical part of this is a find-and-replace; the part that needs attention is code that treated the response as a mapping rather than as a record. Calls to `.get("field")` with a default, `in` checks for optional keys, iteration over `.keys()`, and `json.dumps(result)` all break. Optional fields are now typed as `X | None` and are always present as attributes, so `result.get("cursor")` becomes `result.cursor` and the `None` check stays where it was. For serialisation, use `dataclasses.asdict(result)` or the response type's own `to_dict()` where one exists.

## `fetch_all()` is gone

`Client.fetch_all()` materialised the entire result set in memory and has been removed rather than deprecated in place. `Client.iterate()` replaces it and yields one page at a time:

```python
# v2
for item in client.fetch_all(query):
    handle(item)

# v3
for page in client.iterate(query):
    for item in page.items:
        handle(item)
```

Note the shape change: `fetch_all()` yielded items, `iterate()` yields pages, so a direct substitution will hand you page objects where your code expects records. If you genuinely need the whole set in memory and the size is bounded, `[item for page in client.iterate(query) for item in page.items]` is the honest spelling of what the old method did.

## Timeouts

A timeout is now a `Timeout` object with separate `connect` and `read` values rather than a single float of seconds, and passing a float raises `TypeError` instead of warning. To preserve v2 behaviour exactly, apply the old value to both fields: `timeout=30.0` becomes `timeout=Timeout(connect=30.0, read=30.0)`. In most cases you will want a shorter connect timeout than read timeout, since a connection that has not been established in a few seconds is usually not going to be. Because the failure is a `TypeError` at call time rather than at import, timeouts set in rarely-exercised code paths are the most common thing to survive the upgrade undetected; grep for the keyword rather than relying on the test suite to find them.

## What you get in return

Three additions need no migration work but may let you delete code. `AsyncClient` mirrors the synchronous API and takes the same `ClientConfig`, with `iterate()` becoming an async generator. Rate limiting is handled internally: a 429 response is retried automatically with the `Retry-After` header honoured, so hand-rolled backoff wrappers around v2 calls can usually go. Structured logging hooks let you attach a handler that receives request and response metadata as fields rather than as formatted strings, which replaces the practice of subclassing the client to log around each method.