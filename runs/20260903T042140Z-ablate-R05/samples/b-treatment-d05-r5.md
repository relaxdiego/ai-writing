# Migrating from v2 to v3

v3 changes the shape of the client's public API in five ways, all of which are visible at the call site and none of which can be shimmed silently. There is no codemod. The upgrade is mechanical, but it touches every construction of a client, every place a result is unpacked, and anywhere a timeout is passed.

## Upgrade in two steps

Go to v2.9 first. That release is API-compatible with the rest of the v2 line, and it emits a `DeprecationWarning` for each pattern that v3 removes. Run your test suite with warnings made visible and, ideally, fatal:

```
python -W error::DeprecationWarning -m pytest
```

Fix every warning under v2.9 and commit that work on its own. Once the suite is clean, the move to v3 is a version bump, because the warnings and the breakages cover the same set of call sites. Skipping v2.9 is possible but means discovering the same problems as `TypeError`s at runtime rather than as a list you can work through.

## Python 3.10 is the minimum

v3 drops 3.8 and 3.9. If your project still supports 3.8, resolve that before anything else, since it constrains whether you can upgrade at all. Update your CI matrix and your packaging metadata in the same commit as the version bump so the two never disagree.

## Client construction takes a config object

`Client(url, token)` is gone in favour of a single `ClientConfig`:

```python
# v2
client = Client("https://api.example.com", token)

# v3
client = Client(ClientConfig.from_url("https://api.example.com", token))
```

`from_url` covers the two-argument case exactly, so most call sites are a one-line change. Where you were previously passing extra keyword arguments to `Client`, they now belong as fields on `ClientConfig`, which has the advantage that a configuration can be built once, validated, and reused across several clients rather than reassembled at each construction.

## Results are dataclasses, not dicts

Every method that returned a `dict` now returns a typed dataclass, so key access becomes attribute access:

```python
# v2
for item in result["items"]:
    print(item["name"])

# v3
for item in result.items:
    print(item.name)
```

The practical consequence is that a typo is now an `AttributeError` at the call site instead of a `KeyError` deep in your own code, and that your type checker can see the shape of a response. Code that treated results as generic mappings needs more thought than a search-and-replace: `.get()` with a default, `in` tests, `**result` splatting and `json.dumps(result)` all stop working. Use `dataclasses.asdict(result)` where you genuinely need a mapping, for instance when serialising a response to a log or a cache.

## `fetch_all()` is removed

`fetch_all()` accumulated the whole result set in memory, which was fine for small collections and a liability for large ones. `iterate()` replaces it and yields a page at a time:

```python
# v2
items = client.fetch_all(query)

# v3
for page in client.iterate(query):
    for item in page.items:
        handle(item)
```

If a piece of code truly needs the full list, `list(itertools.chain.from_iterable(p.items for p in client.iterate(query)))` reproduces the old behaviour and its old memory profile, which makes the cost explicit at the one call site that accepts it rather than hiding it behind a method name.

## Timeouts are objects with two values

A float no longer means anything to v3, and passing one raises `TypeError` rather than warning. Connect and read timeouts are now separate:

```python
# v2
client.fetch(query, timeout=30.0)

# v3
client.fetch(query, timeout=Timeout(connect=5.0, read=30.0))
```

A float that used to serve as a single overall budget maps most closely to the read timeout, with a short connect timeout alongside it, since connection setup failing slowly was rarely what the original number was protecting against.

## What you get in return

Three additions come with v3 and require no changes to adopt. `AsyncClient` mirrors the synchronous API with `async`/`await`, including `iterate()` as an async generator. Requests that receive a 429 are retried automatically with the `Retry-After` header honoured, so hand-rolled backoff around the client can usually be deleted. Structured logging hooks let you attach request and response metadata to your own logger rather than parsing the library's log lines.