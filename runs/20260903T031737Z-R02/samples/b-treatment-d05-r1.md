# Migrating from v2 to v3

Version 3 tightens the type surface of the library and removes an API that encouraged unbounded memory use. Most of the work of upgrading is mechanical, but there is no codemod, so plan on touching every call site that constructs a client, reads a result, or sets a timeout. The maintainers recommend a two-step path: upgrade to v2.9 first, which emits a `DeprecationWarning` for every construct removed or changed in v3, fix your code until the warnings stop, and only then move to v3. Running your test suite under `python -W error::DeprecationWarning` during that middle step turns the warnings into failures and gives you a checklist that shrinks to zero.

## Requirements

Python 3.8 support is dropped and the minimum is now 3.10. If you are still on 3.8, do the interpreter upgrade before the library upgrade, since debugging a runtime change and an API change at the same time makes both harder to attribute. Note that v2.9 still runs on 3.8, so you can complete the deprecation-fixing step on your current interpreter and treat the Python upgrade as a separate change.

## Client construction

`Client(url, token)` is gone in favour of a single configuration object, which gives new options a place to live without growing the positional signature further. For the common case there is a constructor helper that takes exactly the old arguments:

```python
# v2
client = Client("https://api.example.com", "tok_123")

# v3
client = Client(ClientConfig.from_url("https://api.example.com", "tok_123"))
```

If you were already passing keyword arguments beyond the URL and token, build the `ClientConfig` directly rather than calling `from_url` and mutating the result, since the config is validated at construction and a field set afterwards may bypass a check.

## Results are dataclasses

Every method that returned a `dict` now returns a typed dataclass, so key access becomes attribute access: `result["items"]` becomes `result.items`. The upside is that your type checker now catches misspelled field names that used to surface as a `KeyError` in production, but the transition is the noisiest part of the upgrade because the failure is silent under a plain grep — a dictionary subscript and a list index look identical. Search for subscripts on the variables you bind from client calls, and be careful with code that treats results as generic mappings: `**result`, `result.get("x")`, `json.dumps(result)`, and iteration over keys all need rewriting. Where you genuinely need a mapping, for logging or serialization, `dataclasses.asdict()` gives you one back.

## `fetch_all()` is removed

`Client.fetch_all()` loaded the entire result set into memory, which is fine for a few hundred records and catastrophic for a few million. Replace it with `Client.iterate()`, which yields one page at a time:

```python
# v2
for item in client.fetch_all(query):
    process(item)

# v3
for page in client.iterate(query):
    for item in page.items:
        process(item)
```

Code that relied on having the whole collection at once — taking `len()`, sorting, indexing backwards — needs a real decision rather than a mechanical rewrite. If the result set is genuinely small and bounded, `list(itertools.chain.from_iterable(p.items for p in client.iterate(query)))` restores the old behaviour explicitly, which at least makes the memory cost visible at the call site. If it is not bounded, this is the moment to push the aggregation into the query or process incrementally.

## Timeouts

Timeouts were a float in seconds and are now a `Timeout` object carrying separate connect and read values, because a single number could not express "fail fast on an unreachable host, but wait a while for a slow query." Passing a float now raises `TypeError` instead of warning:

```python
# v2
client.fetch(query, timeout=30.0)

# v3
client.fetch(query, timeout=Timeout(connect=5.0, read=30.0))
```

The hard failure is deliberate and works in your favour here: unlike the dataclass change, every stale timeout raises loudly the first time that code path runs. Watch for timeouts that arrive from configuration files or environment variables as floats, since those only fail when the relevant path executes and may not be covered by tests.

## What you get in v3

Three additions come with the upgrade and require no changes to adopt. `AsyncClient` mirrors the synchronous API for asyncio callers. Requests that receive a 429 are now retried automatically with the `Retry-After` header honoured, so hand-rolled backoff wrappers around client calls can usually be deleted — check that yours is not also retrying on statuses the library leaves alone. Structured logging hooks let you attach request and response metadata to your own logger instead of parsing the library's log lines.

## Suggested order of work

Start on v2.9 with warnings as errors and fix construction, result access, and timeouts in that order, leaving `fetch_all()` for last because it is the change most likely to need design thought rather than a substitution. Once the suite is clean, bump to v3 and run it again; anything that surfaces at that point is code the deprecation pass could not see, most often dynamic access to result fields or timeouts sourced from configuration.