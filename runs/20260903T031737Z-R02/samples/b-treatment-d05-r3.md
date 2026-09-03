# Migrating from v2 to v3

v3 changes the shape of the client's public surface in five places, and none of the changes can be applied mechanically — there is no codemod. The maintainers recommend a two-step upgrade instead: pin to v2.9 first, which emits a `DeprecationWarning` for every construct listed below, fix your code until the warnings stop, and only then move to v3. Running your test suite under `python -W error::DeprecationWarning` during the v2.9 step turns each warning into a failure and gives you a work-list that shrinks to zero, which is a far more reliable signal than grepping for call sites.

## Requirements

v3 requires Python 3.10 or later; 3.8 support is dropped. If you are still on 3.8, upgrade the interpreter before you touch the library, since doing both at once makes it hard to attribute a failure to either change.

## Construction

`Client(url, token)` is replaced by `Client(config: ClientConfig)`. For the common case where you only have a URL and a token, `ClientConfig.from_url` covers it directly:

```python
# v2
client = Client("https://api.example.com", token)

# v3
client = Client(ClientConfig.from_url("https://api.example.com", token))
```

Constructing `ClientConfig` yourself is worth it once you need to set anything beyond those two fields, and since the config object is plain data you can build it once at startup and pass it around rather than threading a URL and token through your call stack.

## Return values

Every method that returned a `dict` now returns a typed dataclass, so key access becomes attribute access: `result["items"]` becomes `result.items`. The mechanical part of this change is easy; the part that catches people is code that treated the old return value as a generic mapping — `.get("items", [])`, `in` checks, iteration over keys, `json.dumps(result)`. Those do not fail at the call site but somewhere downstream, which is exactly the case v2.9's warnings are there to surface. Where you genuinely need a dict at a boundary (serialising to JSON, say), use `dataclasses.asdict`.

## `fetch_all()` is removed

`Client.fetch_all()` loaded the entire result set into memory and has no v3 equivalent by design. `Client.iterate()` replaces it and yields pages:

```python
# v2
for item in client.fetch_all():
    handle(item)

# v3
for page in client.iterate():
    for item in page.items:
        handle(item)
```

Note the extra loop — `iterate()` yields pages, not items, so a straight substitution will silently hand you page objects where your code expects items. If some call site truly needs the whole set materialised, `list(itertools.chain.from_iterable(p.items for p in client.iterate()))` reproduces the old behaviour, but treat that as a temporary shim rather than a translation, because the memory profile it restores is the reason the method was removed.

## Timeouts

Timeouts are now a `Timeout` object with separate connect and read values, and passing a float raises `TypeError` rather than warning. This is the one change that fails loudly and immediately in v3, so it is easy to find, but it is also the one where the old and new semantics do not line up: a single float had to serve as both budgets, and splitting it means deciding what each half should actually be.

```python
# v2
client.request(url, timeout=30.0)

# v3
client.request(url, timeout=Timeout(connect=5.0, read=30.0))
```

Carrying the old value over to `read` and choosing a short `connect` is a reasonable default, since connection establishment failing slowly is rarely what you wanted from the combined number.

## What you get in return

None of the following requires code changes. `AsyncClient` mirrors the sync client's API for asyncio callers. Requests that receive a 429 are retried automatically with the `Retry-After` header honoured, so hand-rolled backoff around this library can be deleted — and should be, since it will now compound with the built-in retry. Structured logging hooks let you attach the library's request lifecycle to your own logging setup instead of parsing its output.