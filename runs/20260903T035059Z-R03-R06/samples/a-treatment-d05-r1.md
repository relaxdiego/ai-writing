# Upgrading from v2 to v3

v3 changes the constructor signature, the return types, and the timeout argument, removes `fetch_all()`, and raises the minimum Python to 3.10. There is no codemod, so every affected call site has to be visited by hand. What makes that tractable is 2.9: it accepts both the old and new forms and emits a `DeprecationWarning` at each site that will break, so you can find the work by running your test suite instead of by grepping. Move to 2.9, drive the warnings to zero, then change the pin to v3 and expect nothing to move.

## Before you start: Python 3.10

The minimum interpreter is 3.10, so 3.8 and 3.9 both drop out. Raise the interpreter first, on its own, before touching any library code. Mixing an interpreter bump with an API migration means that when something breaks you have two candidate causes, and the interpreter change tends to surface unrelated problems in your other dependencies.

## Step one: move to 2.9

```
pip install 'yourlib>=2.9,<3'
```

Then make the warnings visible. Deprecation warnings are suppressed by default outside of `__main__`, so under pytest add:

```ini
# pyproject.toml
[tool.pytest.ini_options]
filterwarnings = ["error::DeprecationWarning"]
```

That turns every deprecated call into a test failure, which gives you a work queue. If the count is large, start with `always::DeprecationWarning` to get an inventory, fix by category using the sections below, and switch to `error` once you are close.

### Constructing the client

The two positional arguments are replaced by a single config object. For the common case there is a helper that takes exactly the old arguments:

```python
# v2
client = Client("https://api.example.com", token)

# v3
client = Client(ClientConfig.from_url("https://api.example.com", token))
```

If you construct clients in more than a couple of places, this is worth wrapping in a factory of your own now, while you are in the file anyway. The config object is where the new timeout and retry settings live, so a single place to build it will save you the next pass.

### Results are dataclasses, not dicts

Key access becomes attribute access:

```python
# v2
for item in result["items"]:
    print(item["name"])

# v3
for item in result.items:
    print(item.name)
```

The mechanical part is easy. The part that needs thought is code that treated results as dicts rather than as records: `**result` splatting, `result.get("key", fallback)`, iteration over keys, and anything that passed a result straight to `json.dumps`. Splatting and serialization both have a direct fix in `dataclasses.asdict(result)`, which gives you a plain nested dict again, though if you are only doing that to feed a serializer it is usually better to serialize the dataclass properly and drop the intermediate. `.get()` with a default has no equivalent, because a dataclass field is either present in the schema or does not exist; where you were guarding against a missing key, check whether the field is `None` instead, and where you were guarding against a key the server might not send, consult the field's documented optionality rather than guessing.

### `fetch_all()` is gone

`fetch_all()` accumulated every page in memory before returning, which is the reason it was removed. `iterate()` yields pages instead:

```python
# v2
for item in client.fetch_all():
    process(item)

# v3
for page in client.iterate():
    for item in page.items:
        process(item)
```

Note the extra loop: `iterate()` yields pages, not items. If you want a flat stream, `itertools.chain.from_iterable(page.items for page in client.iterate())` gives you one. Resist the temptation to write `list(...)` around that to restore the old call site; it will pass your tests against small fixtures and then reintroduce exactly the memory behaviour the removal was meant to fix. Where you genuinely need the whole set at once, such as sorting across all results, do the accumulation explicitly so the cost is visible at the point where it is paid.

### Timeouts

A float no longer means anything to the client. Timeouts are now an object with separate connect and read values:

```python
# v2
client.request(..., timeout=30.0)

# v3
client.request(..., timeout=Timeout(connect=5.0, read=30.0))
```

Splitting a single number into two is a judgment call rather than a translation. The old value was almost always sized for the read, since that is the slow part, so carrying it over as `read` and giving `connect` something short is usually right: a connection that has not been established in a few seconds is not going to be. This is also the change that fails hardest if you miss it. In 2.9 a float warns, but in v3 it raises `TypeError`, so any call site that only runs in production and not under test will raise there.

## Step two: move to v3

Once the suite runs clean with `error::DeprecationWarning` under 2.9, bump the pin:

```
pip install 'yourlib>=3,<4'
```

The upgrade should be a no-op in behaviour. If something breaks here that 2.9 did not warn about, it is worth reporting, since the warnings are meant to be exhaustive for the changes listed above.

## New in v3

None of the following requires changes, but each is worth a look once you are on v3. `AsyncClient` mirrors the sync API, including `iterate()` as an async generator, so an asyncio codebase no longer needs to push calls to a thread pool. Retry on 429 is now automatic and honours the `Retry-After` header, which means any hand-rolled backoff wrapper you are carrying is probably now doing worse than the library would; check whether yours respects the header before deciding to keep it. Structured logging hooks let you attach a callback that receives request and response metadata as fields rather than as a formatted string, which is what you want if your logs go somewhere that indexes them. The hook signatures are in the reference documentation, and they take the config object, so they slot into the factory you wrote when you fixed the constructor.