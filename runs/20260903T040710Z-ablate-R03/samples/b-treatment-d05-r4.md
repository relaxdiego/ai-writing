# Migrating from v2 to v3

There is no codemod for this release, and the changes touch construction, return types, iteration, and timeouts, so a direct jump from v2.x to v3 tends to surface all of them at once as import errors and `TypeError`s with no indication of which call site caused what. Upgrade to v2.9 first. That release is functionally v2 but emits a `DeprecationWarning` at every site that v3 will break, which turns the migration into a list you can work through with the test suite green the whole time. Run your tests with `-W error::DeprecationWarning` once you are on 2.9 and the warnings become failures you can fix one at a time; when the run is clean, the bump to v3 is close to a no-op.

Before any of that, check your interpreter. v3 requires Python 3.10 or later, and 3.8 is no longer supported at all. If you are still on 3.8, do that upgrade as its own change, separate from this one, so that a failure has only one possible cause.

## Constructing a client

`Client(url, token)` is gone in favour of a single configuration object, which is what makes room for the retry and logging settings described below. For the common case there is a constructor that takes exactly the old arguments:

```python
# v2
client = Client("https://api.example.com", token)

# v3
client = Client(ClientConfig.from_url("https://api.example.com", token))
```

If you were passing other keyword arguments to `Client`, they now belong on `ClientConfig`, and 2.9 will name each one in its warning.

## Return types

Every method that returned a `dict` now returns a dataclass, so key access becomes attribute access and `result["items"]` becomes `result.items`. This is the change most likely to reach code you did not think of as touching the library, since dictionaries tend to get passed around, unpacked, and serialised far from the call that produced them. The compiler will not help you here, but a type checker will: if you run mypy or pyright over the codebase after upgrading, the subscript operations on the new dataclasses are reported as errors and give you a complete work list. Where you genuinely need a dictionary, for JSON serialisation or an existing internal interface, call `dataclasses.asdict(result)` at the boundary rather than reverting the whole path.

## Iteration replaces `fetch_all`

`Client.fetch_all()` has been removed rather than deprecated in place, because its behaviour was the problem: it accumulated the entire result set in memory before returning anything. `Client.iterate()` yields pages instead, so memory stays flat and the first page is available immediately.

```python
# v2
for item in client.fetch_all(query):
    process(item)

# v3
for page in client.iterate(query):
    for item in page.items:
        process(item)
```

The mechanical translation above preserves your existing behaviour. If some caller truly needs the whole set materialised, `[item for page in client.iterate(query) for item in page.items]` reproduces the old semantics, memory profile included, and it is worth leaving a comment saying so.

## Timeouts

A timeout is now a `Timeout` object carrying separate connect and read values, and passing a float raises `TypeError` rather than warning, so this one fails loudly at runtime rather than quietly changing behaviour. The old single float applied to the whole request; the closest equivalent is to give both fields that value, though it is usually better to set a short connect timeout and a longer read timeout:

```python
# v2
client.fetch(query, timeout=30.0)

# v3
client.fetch(query, timeout=Timeout(connect=5.0, read=30.0))
```

Because the failure is a `TypeError` at call time rather than an import error, a timeout passed only on an error path can survive the migration and fail in production. Grep for `timeout=` across the codebase rather than relying on tests to find them.

## What you get in return

Three additions come with v3 and none of them require changes to adopt. `AsyncClient` mirrors the synchronous API with the same configuration object, so an async call site is the same code under `await`. Rate limiting is handled for you: a 429 response is retried automatically with the `Retry-After` header honoured, which means any hand-rolled backoff wrapped around your v2 calls can probably be deleted, and should be, since two retry layers compound into much longer waits than either intends. Structured logging hooks are configured on `ClientConfig` and emit request and retry events as records with fields rather than formatted strings.

## Order of work

Bump to 2.9 and leave the code alone; confirm the test suite still passes. Turn deprecation warnings into errors and fix them in the order the failures come, which will usually mean client construction first, then the dictionary access, then timeouts. Replace `fetch_all` calls with `iterate` by hand, since 2.9 can warn about them but cannot rewrite the loop body. Run a type checker to catch the dictionary access that the tests never exercised, grep for `timeout=`, and only then move the pin to v3.