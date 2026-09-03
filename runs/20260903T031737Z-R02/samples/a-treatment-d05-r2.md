# Migrating from v2 to v3

Version 3 is a breaking release: the constructor signature changed, return types changed, one method was removed, and the minimum Python version moved to 3.10. There is no codemod, but you do not have to find the affected call sites by hand either. Version 2.9 emits a deprecation warning at every point that v3 breaks, so the recommended path is to upgrade to 2.9 first, let your test suite and a representative run of your application tell you where the problems are, fix them all while still on a working version, and only then move to 3.0. Each individual fix below is small; the value of the two-step route is that the compiler-like feedback loop finds the sites for you instead of leaving you to grep.

## Before you begin: Python 3.10

Python 3.8 support is dropped and 3.10 is the new minimum. Since this is the one change that no amount of source editing will work around, check it first — if you are pinned to 3.8 by another dependency or by your deployment image, resolve that before touching this library, because the rest of the migration is wasted effort until the interpreter is in place. Version 2.9 itself still runs on 3.8, so you can complete the whole warning-fixing step on your current interpreter and treat the version bump as a separate, isolated change.

## Step one: move to 2.9 and surface the warnings

Pin to `2.9` and run your tests with deprecation warnings made visible, or better, made fatal. Python hides `DeprecationWarning` by default in most contexts, so an ordinary test run may report nothing at all even though every call site is warning internally. Under pytest, add:

```ini
[pytest]
filterwarnings =
    error::DeprecationWarning
```

or run once with `python -W error::DeprecationWarning` to get a traceback at the first offending call. If your test coverage of the library is thin, run the application against a staging environment with `-W always::DeprecationWarning` and collect the logs; the warnings name the specific parameter or method, so the resulting list is a work queue rather than a vague signal.

## The four source-level changes

### Client construction

The constructor no longer takes a URL and token positionally; it takes a single `ClientConfig`. For the common case where you only have those two values, `ClientConfig.from_url` gives you the old ergonomics back in one extra call:

```python
# v2
client = Client("https://api.example.com", token)

# v3
client = Client(ClientConfig.from_url("https://api.example.com", token))
```

If you are constructing clients in more than two or three places, this is a good moment to introduce a single factory function in your own code, since a config object is easier to extend later than a positional signature — the new retry and logging settings described below are configured through `ClientConfig`, and centralizing construction now means you set them once.

### Dicts become dataclasses

Every method that returned a `dict` now returns a typed dataclass, so key access becomes attribute access:

```python
# v2
for item in result["items"]:
    print(item["name"])

# v3
for item in result.items:
    print(item.name)
```

Under 2.9 the old key access still works and warns, which is what makes this change tractable: you can convert the call sites one at a time with the suite green after each. Two patterns need more than a mechanical rewrite. Code that does `result.get("name", default)` has no direct equivalent, because the dataclass fields are statically known — a missing field is now a typo you want to hear about at import time, and an optional field is `None`, so `result.name or default` is usually the honest translation. Code that serializes results by passing the dict straight to `json.dumps` should switch to `dataclasses.asdict(result)`, and if you were relying on the wire format being preserved exactly, compare the output before and after, since field names in the dataclasses follow Python conventions and may not match the raw API keys.

### `fetch_all()` is gone

`fetch_all()` accumulated the entire result set in memory, which is why it was removed rather than deprecated in place. `iterate()` yields pages, so the replacement depends on what you were doing with the list. Streaming consumers become slightly simpler:

```python
# v2
for item in client.fetch_all(query):
    process(item)

# v3
for page in client.iterate(query):
    for item in page.items:
        process(item)
```

If you genuinely need the whole set materialized — you sort it, or take a length, or hand it to something that requires a sequence — you can flatten it explicitly with `[item for page in client.iterate(query) for item in page.items]`. Writing it out this way keeps the memory cost visible at the call site instead of hiding it behind a method name, and it gives you an obvious place to add a bound if the result set later grows past what one process can hold.

### Timeouts

Timeouts are now a `Timeout` object with separate connect and read values, and passing a float raises `TypeError` rather than warning:

```python
# v2
client.fetch(query, timeout=30.0)

# v3
client.fetch(query, timeout=Timeout(connect=5.0, read=30.0))
```

The old single float behaved as an overall read timeout, so `Timeout(connect=<something small>, read=<your old value>)` preserves your effective behavior while giving you a much tighter failure signal for unreachable hosts. Pick a connect timeout of a few seconds unless you are talking to something known to be slow to accept connections; the point of splitting the values is that a host that never answers should fail fast rather than consuming the full read budget.

## Step two: move to 3.0

Once 2.9 runs clean with warnings as errors, bump the pin to `3.0` and bump your Python floor to 3.10 in `pyproject.toml` or equivalent. The remaining failures at this point are almost always type annotations that still say `dict[str, Any]`, mocks and test fixtures that return dictionaries where the code now expects dataclasses, and any leftover float timeout on a path your tests do not cover. Run your type checker if you have one — this is the release where it starts earning its keep, since the dataclasses give it something to check that the old dict returns did not.

## What you get on the other side

Three additions arrive with v3 and require no changes to adopt. `AsyncClient` mirrors the synchronous API, including `iterate()` as an async generator, so an async migration is a separate and mostly mechanical piece of work you can schedule whenever it suits you. Retries on HTTP 429 now happen automatically and honor the `Retry-After` header, which means any hand-rolled backoff you wrote around rate limiting is now redundant and should be removed rather than left to compound with the built-in behavior. Structured logging hooks let you attach request and response metadata to your own logger through `ClientConfig`, which is worth wiring up during the migration while the call sites are already open in front of you.