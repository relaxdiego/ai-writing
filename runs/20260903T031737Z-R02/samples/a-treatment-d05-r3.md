# Migrating from v2 to v3

## Take the trip in two hops

v3 removes several APIs outright and turns one soft failure into a hard one, so upgrading directly from an older v2 release means discovering every incompatibility as a traceback at runtime. The maintainers recommend pinning to **v2.9** first: it keeps all the v2 behaviour working but emits a `DeprecationWarning` for each construct that v3 drops. Run your test suite with warnings made visible (`python -W error::DeprecationWarning -m pytest`, or `PYTHONWARNINGS=error::DeprecationWarning`), fix everything the warnings point at, and only then bump the pin to v3. Code that runs clean under v2.9 with warnings as errors should need no further changes.

There is no codemod. The changes below are mechanical enough to do with grep and a careful eye, and the warning messages in v2.9 name the call site, so the work is bounded by how many call sites you have rather than by how hard each one is.

Before any of this, confirm your interpreter. v3 requires **Python 3.10 or newer** and Python 3.8 is no longer supported, so if you are still on 3.8 that upgrade has to land first — otherwise `pip install` will simply refuse to resolve v3 and you will be debugging your package manager instead of your code.

## Constructing a client

The two-positional-argument constructor is gone in favour of a single configuration object, which gives the library somewhere to put the growing set of connection options without another decade of positional parameters. For the common case there is a helper that takes exactly what you used to pass:

```python
# v2
client = Client("https://api.example.com", "tok_abc123")

# v3, simple case
client = Client(ClientConfig.from_url("https://api.example.com", "tok_abc123"))

# v3, when you need to set other options
client = Client(ClientConfig(
    url="https://api.example.com",
    token="tok_abc123",
    timeout=Timeout(connect=3.0, read=30.0),
))
```

If you construct clients in more than a couple of places, it is worth adding a small factory in your own code that builds the `ClientConfig` and returns the client, so the next configuration change touches one function rather than every module that talks to the API.

## Returned values are dataclasses, not dicts

Every method that used to hand back a `dict` now returns a typed dataclass, so subscripting is replaced by attribute access throughout:

```python
# v2
result = client.get_report(report_id)
for item in result["items"]:
    print(item["name"], item["created_at"])

# v3
result = client.get_report(report_id)
for item in result.items:
    print(item.name, item.created_at)
```

The payoff is that your editor and type checker now know the shape of a response, and a typo in a field name fails at check time rather than as a `KeyError` in production. The cost is that anything downstream treating responses as plain dicts needs attention: `json.dumps(result)` will raise, `result.get("field")` no longer exists, and `**result` unpacking stops working. For serialisation, convert explicitly with `dataclasses.asdict(result)`; for optional fields, the dataclass declares them with a default, so read the attribute and compare against `None` instead of reaching for `.get()`. Code that stored raw responses in a cache or queue is the sharp edge here, since the failure surfaces at deserialisation time in a different process — grep for places where a response crosses a serialisation boundary and handle those first.

## `fetch_all()` is removed; use `iterate()`

`fetch_all()` accumulated every page in memory before returning, which was fine for small result sets and pathological for large ones. v3 removes it and exposes `iterate()`, which yields one page at a time and fetches the next only when you ask for it:

```python
# v2
for item in client.fetch_all(query):
    process(item)

# v3
for page in client.iterate(query):
    for item in page.items:
        process(item)
```

Note that `iterate()` yields **pages**, not individual records, so the flat loop becomes a nested one. If you would rather keep call sites flat, flatten once at the boundary with `itertools.chain.from_iterable(page.items for page in client.iterate(query))` and iterate that. Resist the temptation to write `list(...)` around the whole thing to restore the old behaviour — it reintroduces exactly the memory profile the removal was meant to fix, and it will be your largest customer's result set that finds the limit.

## Timeouts are objects, and floats now raise

Splitting connect and read timeouts lets you fail fast on an unreachable host while still allowing a slow query to finish, which a single scalar cannot express. Passing a bare float raised a warning in v2.9 and raises `TypeError` in v3, so there is no silent-misbehaviour window to worry about — the calls either fail immediately or are already correct:

```python
# v2
client = Client(url, token, timeout=30.0)

# v3
client = Client(ClientConfig.from_url(url, token, timeout=Timeout(connect=3.0, read=30.0)))
```

Do not simply copy your old scalar into both fields. A 30-second connect timeout means a dead host ties up a worker for half a minute before you learn anything, so a low single-digit connect value with your previous scalar as the read value is usually the right translation. Per-call timeout overrides follow the same rule and need the same treatment.

## What you get in return

Three additions arrive with v3 and none of them require changes on your side. `AsyncClient` mirrors the synchronous API with `async`/`await` and takes the same `ClientConfig`, so an async migration is a separate, optional project rather than something bundled into this upgrade. Automatic retry on HTTP 429 honours the `Retry-After` header, which means any hand-rolled backoff you wrapped around v2 calls is now duplicated work — check for retry decorators and sleep loops around client calls and delete the ones that only handled rate limiting, keeping any that cover errors the library does not retry. Structured logging hooks let you attach your own logger to request and response events instead of scraping the library's log output; the exact hook signatures are in the reference documentation, and wiring them up is worth doing while you already have the call sites open.

## Checklist

- [ ] Interpreter is Python 3.10 or newer
- [ ] Pinned to v2.9, test suite green with `DeprecationWarning` as error
- [ ] All `Client(url, token)` calls converted to `ClientConfig`
- [ ] Key access on responses converted to attribute access, including serialisation boundaries
- [ ] `fetch_all()` call sites converted to `iterate()` without re-buffering
- [ ] Float timeouts converted to `Timeout`, with connect and read set independently
- [ ] Redundant 429 retry logic removed
- [ ] Pin bumped to v3, suite green again

---

A note on the examples: your brief specified `ClientConfig.from_url`, `Client.iterate`, and the connect/read split, but not the full keyword signatures of `ClientConfig` and `Timeout`, nor the logging hook API. I wrote those examples in the most natural shape consistent with the brief and kept the hook section deliberately non-specific — check them against the real signatures before publishing.