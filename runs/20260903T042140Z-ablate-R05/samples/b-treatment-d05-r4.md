# Upgrading from v2 to v3

Do not jump straight to v3. The maintainers ship v2.9 specifically as a bridge release: it behaves identically to v2.8 at runtime but emits a `DeprecationWarning` at every call site that v3 will break. Upgrading to v2.9 first, fixing every warning while your test suite still passes, and only then bumping to v3 turns a large ambiguous migration into two small verifiable ones. There is no codemod, so the warnings are the only mechanical inventory you will get of the work ahead.

Start by pinning `>=2.9,<3` and running your test suite with warnings promoted to errors, either through `python -W error::DeprecationWarning -m pytest` or a `filterwarnings = ["error::DeprecationWarning"]` entry in your pytest config. Each failure is one line to change. Note that v2.9 still supports Python 3.8, so you can complete this entire pass on your current interpreter and keep the interpreter upgrade as a separate, independently revertable change.

## Construction

`Client(url, token)` is gone in favour of a single config object, which is where all future connection options will live rather than accumulating as positional arguments. For the common case the constructor helper is a direct substitution:

```python
# v2
client = Client("https://api.example.com", token)

# v3
client = Client(ClientConfig.from_url("https://api.example.com", token))
```

If you were already passing keyword arguments beyond the URL and token, build the `ClientConfig` explicitly instead of routing through `from_url`, since the helper only covers the two-argument form.

## Return values are dataclasses

Every method that returned a `dict` now returns a typed dataclass, so `result["items"]` becomes `result.items`. The mechanical replacements are easy to spot; the ones worth searching for deliberately are the idioms that only work on mappings. `result.get("items", [])` has no dataclass equivalent and must become an attribute access, using `getattr(result, "items", [])` only if the field genuinely may not exist. Code that unpacks a result with `**result`, iterates its keys, or passes it to `json.dumps` will fail at runtime rather than at import, so grep for those patterns rather than trusting the type checker to find them. Where you need a mapping back, `dataclasses.asdict(result)` gives you one, which is usually the right fix at the serialisation boundary and the wrong fix everywhere else.

The upside is that your type checker now sees these fields. Running mypy or pyright after this step will surface typos and wrong assumptions about the response shape that the `dict` version silently tolerated.

## `fetch_all()` is removed

`fetch_all()` loaded the entire result set into memory, which was fine for the fixtures it was tested against and less fine in production. `iterate()` replaces it by yielding one page at a time:

```python
# v2
for item in client.fetch_all(query):
    process(item)

# v3
for page in client.iterate(query):
    for item in page.items:
        process(item)
```

If you truly need the whole set materialised, `[item for page in client.iterate(query) for item in page.items]` reproduces the old behaviour, including the memory profile that motivated the removal. Prefer it as a temporary shim in code you intend to revisit rather than as the permanent translation.

## Timeouts

Timeouts were a float in seconds covering the whole operation and are now a `Timeout` object separating the connection phase from the read phase. Passing a float raises `TypeError` in v3 rather than warning, so any call site the v2.9 pass missed will fail loudly at runtime:

```python
# v2
client.fetch(query, timeout=30.0)

# v3
client.fetch(query, timeout=Timeout(connect=5.0, read=30.0))
```

Splitting one number into two is a judgement call rather than a translation. A short connect timeout with a generous read timeout is the usual shape, since failing to establish a connection is rarely worth waiting on while a slow response often is. Reusing your old value for both fields is safe but doubles your worst-case wall time.

## Python version

The minimum supported version is 3.10. Because v2.9 still runs on 3.8, sequence the interpreter upgrade between the two library upgrades: fix the deprecation warnings on your current runtime, deploy that, then move the interpreter, then take v3. Doing both at once means any failure leaves you guessing which change caused it.

## What you get in return

Three additions land in v3 without requiring any changes on your side. `AsyncClient` mirrors the synchronous API for asyncio callers. Retries on HTTP 429 are now automatic and honour the `Retry-After` header, so hand-rolled backoff wrappers around v2 calls can usually be deleted, and you should check that yours is not now retrying on top of the library's retries. Structured logging hooks let you attach request and response metadata to your own logger rather than parsing the library's log lines.