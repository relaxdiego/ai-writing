# Migrating from v2 to v3

v3 changes how the client is constructed, how results are typed, and how timeouts are expressed. There is no codemod, but there is a supported path that keeps you from making all the changes blind: upgrade to v2.9 first, which emits a `DeprecationWarning` for every construct listed below, fix your code until the warnings are silent, and only then move to v3. Running your test suite under `python -W error::DeprecationWarning` turns that into a hard failure list rather than log noise you have to read. If you skip the intermediate step you will find the breakages anyway, but at runtime and one at a time.

Before any of it, check your Python version. v3 requires 3.10 or later, and 3.8 is no longer supported. The typed results depend on features that are not available on older interpreters, so this one is not negotiable and there is no compatibility shim.

## Constructing the client

`Client(url, token)` is gone; the constructor now takes a single `ClientConfig`. For the common case where you only have a URL and a token, `ClientConfig.from_url` gives you the old ergonomics back in one extra call:

```python
# v2
client = Client("https://api.example.com", token)

# v3
client = Client(ClientConfig.from_url("https://api.example.com", token))
```

If you were passing other keyword arguments to the constructor, they now belong on the config object, which is also where the new retry and logging settings live. Building the config explicitly is worth it as soon as you need more than the two fields.

## Results are dataclasses, not dicts

Every method that used to return a `dict` now returns a typed dataclass, so key access becomes attribute access:

```python
# v2
for item in result["items"]:
    print(item["name"])

# v3
for item in result.items:
    print(item.name)
```

The mechanical part of this is easy; the part that catches people is code that treats results as generic mappings. Calls to `.get()`, `in` checks, `json.dumps(result)`, `**result` splatting and anything that iterates over keys will now raise `AttributeError` or `TypeError` rather than quietly returning something wrong. Search for those patterns specifically, since v2.9 cannot warn about them: it can only warn where the library itself hands you a value. Use `dataclasses.asdict(result)` where you genuinely need a dictionary, for serialisation at a boundary you do not control.

## `fetch_all()` is removed

`fetch_all()` loaded the entire result set into memory, which is why it is gone rather than deprecated in place. `iterate()` yields pages instead, so the replacement is a nested loop:

```python
# v2
for item in client.fetch_all():
    process(item)

# v3
for page in client.iterate():
    for item in page.items:
        process(item)
```

If some call site really does need everything at once, write the accumulation yourself so the memory cost is visible at the place that pays it, using `itertools.chain.from_iterable(page.items for page in client.iterate())` to flatten. Prefer streaming where you can; the reason the old method was removed is that most callers did not need the whole set.

## Timeouts

A timeout is now a `Timeout` object carrying separate connect and read values rather than a single float of seconds. Passing a float raises `TypeError` immediately instead of warning, so this change fails loudly and you will not ship it by accident:

```python
# v2
client.get(path, timeout=30.0)

# v3
client.get(path, timeout=Timeout(connect=5.0, read=30.0))
```

The old single value almost always meant the read timeout, so `Timeout(connect=5.0, read=<old value>)` is a faithful translation. Splitting the two is the point of the change: a slow connect and a slow response usually want different limits and different retry behaviour.

## What you get in return

Three additions come with v3, none of which require changes to existing code. There is an `AsyncClient` with the same surface as the synchronous one, so an async codebase no longer needs a thread pool to call the library. Requests that receive a 429 are now retried automatically with the `Retry-After` header honoured, which means you can delete hand-rolled backoff wrappers around these calls, and should, because two layers of retry compound into much longer waits than either intends. Structured logging hooks let you attach request and response metadata to your own logger rather than parsing what the library prints.

The retry behaviour is the one addition worth auditing rather than simply enjoying. Code that previously caught a 429 and handled it as a rate-limit signal will now see that exception far less often, because the library absorbs it, and any metric or alert built on that exception will go quiet.