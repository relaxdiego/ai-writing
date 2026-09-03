# Migrating from v2 to v3

v3 changes the client constructor, the return types of every method, the timeout API, and the minimum Python version. There is no codemod, so plan on touching each call site by hand. The upgrade is much easier if you do it in two passes: move to v2.9 first, which still behaves like v2 but emits a `DeprecationWarning` for every pattern that v3 removes. Run your test suite with `-W error::DeprecationWarning` and fix what surfaces. Once the suite is clean under v2.9, the jump to v3 is mostly a version bump.

Before any of that, confirm you are on Python 3.10 or later. v3 drops 3.8, and since 3.9 also passed end of life the floor is 3.10. If you are still on 3.8, do that upgrade on its own, separately from the library change, so that a failure has one obvious cause.

## Constructing a client

The two-positional-argument constructor is gone in favour of a config object, which is what makes room for the retry and logging settings described below.

```python
# v2
client = Client("https://api.example.com", token)

# v3
client = Client(ClientConfig.from_url("https://api.example.com", token))
```

`ClientConfig.from_url` covers the simple case and is the mechanical translation for most call sites. Where you were previously threading a URL and token through your own helpers, consider building a `ClientConfig` once at startup and passing that instead, since it also carries the timeout and retry configuration.

## Typed results instead of dicts

Every method that returned a `dict` now returns a dataclass, so key access becomes attribute access: `result["items"]` becomes `result.items`, and `result["page"]["next"]` becomes `result.page.next`. Code that iterated over keys, called `.get()` with a default, or serialised results directly with `json.dumps` will break at runtime rather than at import, which is the main reason to lean on v2.9's warnings rather than grepping for square brackets. For the places that genuinely need a mapping, `dataclasses.asdict` gives you one back. Typed results are also the payoff of the change: your type checker can now see the shape of a response, and a misspelt field is an error before you ship it.

## `fetch_all()` is removed

`fetch_all()` loaded an entire result set into memory, which was fine for a few hundred records and a problem for a few hundred thousand. Use `iterate()`, which yields pages.

```python
# v2
for item in client.fetch_all():
    handle(item)

# v3
for page in client.iterate():
    for item in page.items:
        handle(item)
```

If some call site really does need the whole set materialised, write `[item for page in client.iterate() for item in page.items]` and keep that decision visible at the point where it is made.

## Timeouts

Timeouts are now a `Timeout` object with separate connect and read values, and passing a float raises `TypeError` instead of warning. This one fails loudly, so it is the least likely to slip through, but it is worth choosing the two values deliberately rather than splitting your old number in half. Connect timeouts should be short, a second or two, since a connection that has not been established quickly usually will not be. Read timeouts should reflect how long the slowest endpoint you call legitimately takes.

```python
# v2
client = Client(url, token, timeout=30.0)

# v3
config = ClientConfig.from_url(url, token, timeout=Timeout(connect=2.0, read=30.0))
```

## What you gain

Three additions need no migration work but may let you delete some of your own code. `AsyncClient` mirrors the synchronous API for use under `asyncio`. Retries on HTTP 429 are now automatic and honour the `Retry-After` header, so any hand-rolled backoff loop wrapping your v2 calls can probably go. Structured logging hooks let you attach request and response metadata to your existing logging setup without monkey-patching the transport.

## Suggested order of work

Bump to v2.9 and turn deprecation warnings into errors in CI. Fix the constructor calls, the dict access, the `fetch_all()` uses, and the float timeouts until the suite is green. Commit that, because it is a working state on the old major version and a safe place to stop if you run out of time. Then bump to v3 and run the suite again; what remains will be the dynamic dict access that v2.9 could not see, which is usually a handful of serialisation sites and test fixtures.