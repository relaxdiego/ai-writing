# Migrating from v2 to v3

There is no codemod for this upgrade, so every call site has to be visited by hand. The maintainers recommend doing that in two passes rather than one. Pin to v2.9 first, which still accepts all the v2 spellings but emits a `DeprecationWarning` for each one that v3 removes. Run your test suite with `-W error::DeprecationWarning` and the interpreter will point you at the exact lines that need attention, which is a far better inventory than grepping. Once 2.9 is warning-clean, the bump to v3 is usually a version change and a green test run. Doing it in a single jump is possible but you lose the compiler-like feedback, and several of the changes below fail at runtime rather than at import, so a silent gap in test coverage becomes a production error instead of a warning.

## Python version

v3 requires Python 3.10 or newer; 3.8 and 3.9 are no longer supported. Do this part first and separately, because it is the one change that can block the others: the typed return values lean on modern typing features, and if your deployment target is still on 3.8 the rest of the migration has nowhere to land. If you cannot move the runtime yet, stay on 2.9, which keeps 3.8 support and still gives you the deprecation warnings, so the work is not wasted.

## Constructing a client

`Client(url, token)` is gone in favour of a single configuration object:

```python
# v2
client = Client("https://api.example.com", token)

# v3
client = Client(ClientConfig.from_url("https://api.example.com", token))
```

`ClientConfig.from_url` covers the two-argument case and is the mechanical substitution for most call sites. Reach past it and build a `ClientConfig` directly when you need to set timeouts, retry behaviour, or logging hooks, since those now live on the config rather than being scattered across keyword arguments.

## Return values are dataclasses

Every method that returned a `dict` now returns a typed dataclass, so key access becomes attribute access:

```python
# v2
for item in result["items"]:
    print(item["name"])

# v3
for item in result.items:
    print(item.name)
```

This is the change most likely to hide in code your tests do not exercise, because `result["items"]` on a dataclass raises `TypeError` at the moment it runs and not a line earlier. Pay particular attention to anywhere a response was passed to `json.dumps`, merged with `**`, or fed into code that duck-types dictionaries; those sites need `dataclasses.asdict(result)` rather than a rename. Code that used `.get("field")` to tolerate a missing key should become `getattr(result, "field", None)` only where the field is genuinely optional. Where it is not, the dataclass now guarantees presence and the defensive branch can go.

## `fetch_all()` is removed

`fetch_all()` accumulated the whole result set in memory before returning, which is why it is gone rather than deprecated in place. `iterate()` replaces it and yields a page at a time:

```python
# v2
items = client.fetch_all(query)

# v3
for page in client.iterate(query):
    for item in page.items:
        handle(item)
```

If you genuinely need the full list, `[item for page in client.iterate(query) for item in page.items]` reproduces the old behaviour and the old memory profile, and it is a reasonable stopgap for a small result set. It is worth checking first whether the consuming code can be restructured to work page by page, since that is the benefit the change is offering.

## Timeouts

Timeouts are now a `Timeout` object with separate connect and read values, and passing a float raises `TypeError` instead of warning:

```python
# v2
client = Client(url, token, timeout=30.0)

# v3
config = ClientConfig.from_url(url, token)
config.timeout = Timeout(connect=5.0, read=30.0)
```

A bare v2 float applied to the whole operation, so the closest equivalent is to keep your old value as the read timeout and choose a shorter connect timeout, which is what the split is for: a connection that has not been established in five seconds is not going to be established, whereas a slow response may still be worth waiting on.

## What you get in return

Three additions come with v3 and none of them require changes to migrate. `AsyncClient` mirrors the synchronous API for `asyncio` code. Requests that receive a 429 are now retried automatically with the `Retry-After` header honoured, so hand-rolled backoff around v2 calls can usually be deleted, and you should check for it while you are touching each site. Structured logging hooks are configured on `ClientConfig` and replace whatever you were doing with the library's log records before.

## Suggested order

Move the runtime to 3.10, pin 2.9, and run the tests with deprecation warnings as errors. Fix the constructor and timeout call sites, which are localised and mechanical, then the `fetch_all` call sites, which may need real restructuring. Leave the dict-to-dataclass conversion for last and give it the most care, since it touches the most code and has the least help from the interpreter. Then bump to v3 and run the suite once more.