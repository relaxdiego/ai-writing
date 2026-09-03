# Migrating from v2 to v3

v3 changes how you construct a client, what its methods return, and how timeouts are expressed, and it removes `fetch_all()` along with Python 3.8 support. There is no codemod, so every call site has to be visited by hand. The maintainers recommend doing that under v2.9 rather than under v3: v2.9 accepts both the old and new forms and emits a `DeprecationWarning` for each thing v3 removes, so you can find your call sites while the code still runs. Upgrade to 2.9, run your test suite with warnings surfaced, fix what it reports, and only then bump to 3.x, at which point the pin change should be the only diff.

To make the warnings hard to miss, run the suite with them promoted to errors:

```
python -W error::DeprecationWarning -m pytest
```

or, if that is too blunt for a large suite, `-W default::DeprecationWarning` to print every occurrence rather than only the first per location.

## Python 3.10 is the minimum

v3 drops 3.8 and 3.9. Do this part first if you are still on either, because it is the one change that has nothing to do with the library and can land independently. v2.9 runs on 3.8, so you can sequence the interpreter bump before or after the deprecation cleanup, whichever your CI makes easier.

## Client construction takes a config object

`Client(url, token)` is replaced by `Client(config)`, where the config carries the connection settings that used to be spread across positional and keyword arguments:

```python
# v2
client = Client("https://api.example.com", "tok_abc")

# v3
from library import Client, ClientConfig
client = Client(ClientConfig.from_url("https://api.example.com", "tok_abc"))
```

`ClientConfig.from_url()` exists for exactly this case and is the shortest path for code that passed nothing but a URL and a token. If you were also passing timeouts, retries, or other options, build the config directly instead and set the fields you need; the constructor keyword names match the old ones except for `timeout`, covered below.

## Methods return dataclasses, not dicts

Every method that returned a `dict` now returns a typed dataclass, so key access becomes attribute access:

```python
# v2
result = client.search("widgets")
for item in result["items"]:
    print(item["id"])

# v3
result = client.search("widgets")
for item in result.items:
    print(item.id)
```

The mechanical substitution is easy to grep for, but two habits around dicts do not survive it. `result.get("items", [])` has no equivalent, because a dataclass field is always present; where a field is genuinely optional it is typed `| None` and you check for `None`. And a missing name now raises `AttributeError` at the point of access rather than `KeyError`, which matters mostly for the typo you never noticed because the key was fed straight into a `.get()`. Code that serialised a response by handing it to `json.dumps()` also breaks; use `dataclasses.asdict(result)` to get a plain dict back at the boundary where you actually need one.

## `fetch_all()` is removed in favour of `iterate()`

`fetch_all()` accumulated every page into a single list before returning, which meant peak memory scaled with the size of the result set. `iterate()` yields pages instead, so you hold one page at a time:

```python
# v2
for item in client.fetch_all("widgets"):
    process(item)

# v3
for page in client.iterate("widgets"):
    for item in page.items:
        process(item)
```

If some caller truly needs the whole set materialised, you can write `[item for page in client.iterate("widgets") for item in page.items]`, which reproduces the old behaviour including its memory profile. Prefer restructuring the caller to consume pages where you can, since that is the reason the method was removed.

## Timeouts are a `Timeout` object

A single float meant one budget covering both connecting and reading, which conflated a fast failure on an unreachable host with a slow response from a healthy one. v3 separates them:

```python
# v2
client = Client(url, token, timeout=30.0)

# v3
config = ClientConfig.from_url(url, token, timeout=Timeout(connect=5.0, read=30.0))
client = Client(config)
```

Passing a float raises `TypeError` rather than warning, so this change fails loudly at construction and cannot slip into production unnoticed. Under v2.9 the float is still accepted and warns, which is where you want to catch it. A reasonable default translation is to keep your old value as `read` and set `connect` to something short, in the range of a few seconds, since a connection that has not been established quickly is usually not going to be.

## What v3 adds

None of the following requires changes to migrate, but they may change how you structure the code you are already touching. `AsyncClient` mirrors the synchronous API with `await` and `async for`, taking the same `ClientConfig`. Retries on HTTP 429 are now automatic and honour the `Retry-After` header, so hand-rolled backoff around rate limits can be deleted, and leaving it in place will compound with the built-in retry. Structured logging hooks let you attach a callback that receives request and response metadata as a dataclass rather than parsing it out of log strings.