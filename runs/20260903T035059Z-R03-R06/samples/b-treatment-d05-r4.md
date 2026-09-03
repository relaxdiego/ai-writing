# Migrating from v2 to v3

There is no codemod for this upgrade, so the maintainers recommend doing it in two passes. Install v2.9 first and run your test suite with warnings visible (`python -W error::DeprecationWarning -m pytest`, or set `filterwarnings = error` in your pytest config). Every breaking change described below emits a deprecation warning in 2.9, pointing at the call site, so the warning log is effectively the work list. Once 2.9 runs clean, the move to v3 is mostly a version bump. Doing it in one jump means finding the same problems as `TypeError`s at runtime, in whatever order your code happens to execute.

Before any of that, check your Python version. v3 requires 3.10 or later, and 3.8 is no longer supported. If you are on 3.8, upgrade the interpreter first and keep the library on v2 while you do, since debugging an interpreter upgrade and a library upgrade at the same time gives you two candidate causes for every failure.

## Constructing a client

`Client(url, token)` is gone. The constructor now takes a single `ClientConfig`, which is where retry policy, timeouts and logging hooks also live. For the common case where you only have a URL and a token, use the helper:

```python
# v2
client = Client("https://api.example.com", token)

# v3
client = Client(ClientConfig.from_url("https://api.example.com", token))
```

If you build clients in more than two or three places, it is worth writing a small factory in your own code that returns a configured `ClientConfig`, rather than repeating `from_url` at each call site. The config object is where the new features are configured, so a single construction point will save you editing later when you want retries or logging.

## Dataclasses instead of dicts

Every method that returned a `dict` now returns a typed dataclass, and key access becomes attribute access: `result["items"]` becomes `result.items`. This is the change most likely to be scattered widely through your code, and it is also the one the type checker will find for you. If you are not already running mypy or pyright over the code that touches this library, running it once during the upgrade will locate the call sites faster than grep, because subscript access on a dataclass is a type error rather than a text pattern.

Two habits from the dict era need rewriting rather than translating. `result.get("items", [])` has no attribute equivalent; the field is always present, so read it directly and drop the default. Code that iterated keys, passed results to `json.dumps`, or did `**result` splatting needs `dataclasses.asdict(result)` to get back to a mapping. Where the value was only being logged or serialised, `asdict` at the boundary is usually the smallest change.

## `fetch_all()` is removed

`fetch_all()` loaded the whole result set into memory, and it has been replaced by `iterate()`, which yields pages. The mechanical translation is:

```python
# v2
for item in client.fetch_all(query):
    process(item)

# v3
for page in client.iterate(query):
    for item in page.items:
        process(item)
```

Code that genuinely needed a materialised list can write `[item for page in client.iterate(query) for item in page.items]`, but consider whether it did. Callers that took `len()` of the result, sorted it, or indexed into it are the ones that need the list; callers that looped over it once are better left streaming, which is the reason for the removal.

## Timeouts

Timeouts are now a `Timeout` object with separate connect and read values, and passing a float raises `TypeError` rather than warning. A v2 call of `timeout=30.0` becomes `timeout=Timeout(connect=5.0, read=30.0)` if you want to preserve the old read behaviour with a sensible connect bound. The old float applied to the whole operation, so there is no exactly equivalent translation; pick a connect timeout short enough to fail fast on an unreachable host, and carry your old value over to `read`.

Because this raises rather than warns in v3, a float left anywhere in your code becomes a runtime failure on the first request through that path. Search for `timeout=` across the codebase during the 2.9 pass rather than relying on tests to reach every call.

## What you get in return

Three additions are worth adopting once the upgrade is done, though none of them requires changes to work. `AsyncClient` mirrors the sync API with `await` and `async for`, sharing the same `ClientConfig`. Retries on HTTP 429 are now automatic and honour the `Retry-After` header, so hand-rolled backoff loops around rate-limited calls can be deleted; if you keep them, you will be backing off on top of the library's own backoff. Structured logging hooks are configured on `ClientConfig` and give you request and response events with fields rather than formatted strings, which is where you would attach request IDs or timing to your existing observability setup.