# Migrating from v2 to v3

v3 tightens the API surface in ways that will break most existing code: the constructor signature changed, return values became typed objects, the eager-loading path was removed, and timeouts are no longer bare floats. Python 3.8 and 3.9 are no longer supported, so the minimum interpreter is 3.10. In exchange you get an async client, automatic retry handling for rate limits, and hooks for structured logging.

There is no codemod. The path that will cost you the least is to upgrade to v2.9 first, which emits a `DeprecationWarning` for every construct listed below, then fix warnings until the suite runs clean, and only then move to v3. Run your test suite with `-W error::DeprecationWarning` to make the warnings fail loudly instead of scrolling past.

## Before you start: Python version

Confirm your runtime is 3.10 or newer before touching any library code, since a version bump can surface unrelated failures of its own and you do not want them interleaved with API migration failures. If you are stuck on 3.8 or 3.9 for other reasons, stay on v2.9 — it remains installable and receives the deprecation warnings but none of the breaking changes.

## Constructing a client

The two-positional-argument constructor is gone in favour of a single config object, which gives room for connection settings that previously had nowhere sensible to live.

```python
# v2
client = Client("https://api.example.com", "tok_abc123")

# v3, simple case
client = Client(ClientConfig.from_url("https://api.example.com", "tok_abc123"))

# v3, when you need more
client = Client(ClientConfig(
    url="https://api.example.com",
    token="tok_abc123",
    timeout=Timeout(connect=2.0, read=30.0),
))
```

If your codebase builds clients in one factory function, this is a one-line change. If it constructs them inline across many modules, consider introducing that factory as part of the v2.9 step, while both signatures still work, so the v3 cutover touches a single site.

## Return types

Every method that returned a `dict` now returns a dataclass, so key access becomes attribute access throughout. The rename is mechanical but the failure mode is not: a missed `result["items"]` raises `TypeError: 'PageResult' object is not subscriptable` at runtime rather than at import, so untested code paths will carry the old syntax silently until they execute. Grep for subscript access on call results before you rely on tests to find them all.

```python
# v2
for item in result["items"]:
    print(item["name"])

# v3
for item in result.items:
    print(item.name)
```

Code that treated results as generic mappings — passing them to `json.dumps`, merging them with `**`, or iterating `.keys()` — needs more than a syntax swap. Use `dataclasses.asdict(result)` where you genuinely need a dictionary, and keep in mind that it recurses into nested dataclasses.

## `fetch_all()` is removed

`fetch_all()` loaded the entire result set into memory, which was fine at demo scale and a liability at production scale, and it has no v3 equivalent. `iterate()` replaces it by yielding one page at a time.

```python
# v2
items = client.fetch_all()

# v3, streaming — preferred
for page in client.iterate():
    for item in page.items:
        process(item)

# v3, if you truly need the whole set materialised
items = [item for page in client.iterate() for item in page.items]
```

Reach for the second form only when something downstream needs random access or a length up front. Anything that just loops once should stream, since that is the entire reason the eager method was dropped.

## Timeouts

Timeouts are now a `Timeout` object with separate connect and read values, and passing a float raises `TypeError` instead of warning. The split matters more than it looks: a single number forced you to size one budget for two very different waits, so a value generous enough for a slow response also let a dead host hang. Connect timeouts should generally be small, a couple of seconds, while read timeouts follow whatever your slowest endpoint actually needs.

```python
# v2
client.request(path, timeout=30.0)

# v3
client.request(path, timeout=Timeout(connect=2.0, read=30.0))
```

If you want to preserve v2 behaviour exactly during the migration and tune later, `Timeout(connect=30.0, read=30.0)` reproduces the old semantics closely enough.

## What you get in return

`AsyncClient` mirrors the synchronous API method for method, so a port is largely a matter of adding `await` and using `async for` over `iterate()`. The client now retries automatically on HTTP 429 and honours the `Retry-After` header, which means any hand-rolled rate-limit backoff wrapped around v2 calls can usually be deleted — leaving it in place is harmless but will compound the wait. Structured logging hooks let you attach a handler that receives request and response metadata as fields rather than formatted strings, which is worth wiring up during the migration while you are already touching client construction.

## Suggested order of work

Start by pinning v2.9 and running the suite with deprecation warnings promoted to errors, then work through the constructor and timeout call sites first because they are localised and easy to verify. Handle the `dict`-to-dataclass conversion next, using grep for subscript access to catch paths your tests do not cover, and convert `fetch_all()` callers last since some of them will need real thought about whether they should stream or materialise. Once the suite is clean under v2.9, the bump to v3 should be a version change and nothing more; if it is not, whatever breaks is something the deprecation warnings could not detect statically, and the traceback will point at it directly.