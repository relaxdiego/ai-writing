# Migrating from v2 to v3

v3 changes the shape of the public API in five ways, all of them mechanical once you know what to look for. There is no codemod, so the safest route is the two-step upgrade the maintainers recommend: pin to v2.9 first, where every removal and signature change below emits a `DeprecationWarning`, fix your code until the warnings are silent, and only then move to v3. Going straight to v3 works too, but you trade a list of warnings you can work through incrementally for a pile of `TypeError`s and `AttributeError`s that surface at runtime, often in code paths your tests don't reach.

## Before you begin: Python 3.10

v3 drops Python 3.8; 3.10 is the minimum. Do this part first and separately, because a Python upgrade tends to drag in unrelated dependency churn, and you do not want that churn interleaved with library changes when something breaks. If you are on 3.8 today, get to 3.10 on v2.9 and confirm your suite is green before touching any of the API changes.

## Step 1: pin to v2.9 and turn warnings into work

```
pip install 'yourlib>=2.9,<3'
```

Run your test suite with warnings made visible, and ideally fatal in CI:

```
python -W error::DeprecationWarning -m pytest
```

Every change described below has a corresponding warning in 2.9, so the warning list is your migration checklist. Work through it until the run is clean.

## Client construction

`Client(url, token)` is replaced by `Client(config: ClientConfig)`. For the common case where you have nothing but a URL and a token, the `from_url` helper is a direct substitution:

```python
# v2
client = Client("https://api.example.com", token)

# v3
client = Client(ClientConfig.from_url("https://api.example.com", token))
```

If you were passing other keyword arguments to the constructor, they now belong on `ClientConfig`, which is where the timeout change below also lands. Construct the config once at the edge of your application and pass it around rather than rebuilding it at each call site; that also gives you a single place to change when configuration grows.

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

This is the change most likely to reach production undetected, because a dict lookup on a dataclass raises `TypeError` only when that line actually runs. Search for subscript access on anything the library returns, and pay particular attention to error-handling branches and rarely-exercised endpoints. Two related habits also stop working: `result.get("items", [])` has no equivalent, since a dataclass field is either present in the schema or it isn't, and `json.dumps(result)` will fail, so use `dataclasses.asdict(result)` if you were serialising responses directly. The gain is that your type checker now sees these shapes, so running mypy or pyright over the migrated code will find the remaining call sites for you far more reliably than grep will.

## `fetch_all()` is gone; use `iterate()`

`fetch_all()` loaded the entire result set into memory, which is why it was removed rather than deprecated in place. `iterate()` yields pages, so the replacement is a nested loop:

```python
# v2
for item in client.fetch_all(query):
    process(item)

# v3
for page in client.iterate(query):
    for item in page.items:
        process(item)
```

If some piece of code genuinely needs the whole set at once, say because it sorts or aggregates across everything, you can flatten it yourself with `itertools.chain.from_iterable(page.items for page in client.iterate(query))`. Do that deliberately and locally, though, rather than defining a `fetch_all` shim that restores the old behaviour everywhere: the unbounded memory use was the reason for the removal, and a shim quietly reintroduces it.

## Timeouts are objects, not floats

A timeout is now a `Timeout` with separate connect and read values, and passing a float raises `TypeError` rather than warning. When splitting an existing single value, remember that it previously covered both phases, so reusing it for each gives you a slightly more generous budget overall:

```python
# v2
client = Client(url, token, timeout=30.0)

# v3
config = ClientConfig.from_url(url, token)
config.timeout = Timeout(connect=5.0, read=30.0)
client = Client(config)
```

A short connect timeout with a longer read timeout is usually what you actually wanted: connection setup either succeeds quickly or is not going to succeed, while a slow response is often worth waiting for.

## Step 2: move to v3

With the warnings cleared, `pip install 'yourlib>=3'` should be uneventful. Three additions become available at that point, none of which require changes to working code. `AsyncClient` mirrors the synchronous API, including `iterate()` as an async generator, and takes the same `ClientConfig`. Rate limiting is now handled for you: a 429 response is retried automatically with the `Retry-After` header honoured, so any hand-rolled backoff you wrapped around calls can be deleted, and you should check that such wrappers are not now retrying on top of the library's own retries. Structured logging hooks let you attach request and response metadata to your existing logging setup instead of inferring what happened from timing.

If you cannot do the two-step upgrade because your dependency graph forces a single jump, the ordering that causes the least pain is still the same: Python version, then construction, then timeouts, then dict access, then pagination. Run a type checker after each stage, since the typed return values make the checker the most effective tool you have for finding what you missed.