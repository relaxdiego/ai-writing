# Upgrading from v2 to v3

v3 changes five things that will break existing code, and there is no codemod. What there is instead is v2.9, which emits a deprecation warning for every one of those five. The practical path is two hops rather than one: install 2.9, run your test suite with warnings made visible (`python -W error::DeprecationWarning -m pytest`, or at minimum `-W default`), fix everything it reports, and move to 3.0 only once the run is clean. Taking it in that order means your signal comes from a version that still executes your old code, rather than from a pile of `TypeError`s and `AttributeError`s raised at whatever point your test run happens to reach first.

## Python 3.10 is required

v3 drops Python 3.8 and requires 3.10 or later, so this gates everything else. If your project still runs on 3.8, note that 2.9 supports it: you can do all of the warning-fixing work on your current interpreter, get a clean run, and treat the interpreter bump as a separate change with its own review. Splitting it that way keeps a 3.10 migration from being tangled up with library API changes when something goes wrong.

## `Client` takes a config object

The two-argument constructor is gone in favour of a single `ClientConfig`. For the common case there is a helper that takes exactly the old arguments, so the change is mechanical:

```python
# v2
client = Client("https://api.example.com", token)

# v3
client = Client(ClientConfig.from_url("https://api.example.com", token))
```

If you construct clients in more than a couple of places, this is a good moment to build the config once and pass it around, since everything else that used to be a constructor keyword now lives on the config object.

## Timeouts are a `Timeout` object

A float is no longer accepted; in v3 it raises `TypeError` rather than warning, so there is no grace period once you are on 3.0. The replacement separates the two phases that the single number used to cover:

```python
# v2
timeout=30.0

# v3
timeout=Timeout(connect=5.0, read=30.0)
```

Because the old value conflated connecting and reading, this is not a straight substitution. A single 30-second budget usually meant "give up on a slow response after 30 seconds", and connection setup should fail much sooner than that, so the usual translation is a short connect and a read at or near the old number. Anywhere the old float was tuned deliberately, check what it was tuned against before you split it.

## Methods return dataclasses, not dicts

Every method that returned a `dict` now returns a typed dataclass, so `result["items"]` becomes `result.items`. This is the change most likely to slip through, because dict access spreads further than the call sites themselves: `result.get("items", [])`, `"items" in result`, `json.dumps(result)`, iteration over keys, and anything that passes a result into a function annotated for `Mapping` will all need attention. Subscripting still works in 2.9 and warns, which is what makes the intermediate step worth the trouble; the warning fires at the access, giving you the exact line. Where you were relying on `.get()` for a key that might be absent, an optional field on the dataclass will be `None` instead, so the fallback moves from the accessor to the value.

## `fetch_all()` is removed in favour of `iterate()`

This is the one change that is not just a syntax edit, because `fetch_all()` was removed for a reason: it built the entire result set in memory. `iterate()` yields pages, so the shape of the loop changes:

```python
# v2
for item in client.fetch_all():
    handle(item)

# v3
for page in client.iterate():
    for item in page:
        handle(item)
```

If you prefer a flat iterator, `itertools.chain.from_iterable(client.iterate())` gives you one without materialising anything. You can also reproduce the old behaviour exactly with `[item for page in client.iterate() for item in page]`, and that is the right move for code that calls `len()` on the result, indexes into it, or iterates it more than once. Doing so keeps the old memory profile too, so treat it as a stopgap rather than the destination.

## What you get on the other side

Three additions arrive with v3 and require no changes to adopt. `AsyncClient` mirrors the sync API for use under `asyncio`. Retries on HTTP 429 are now automatic and honour the `Retry-After` header, which means any hand-rolled retry loop around 429 should come out: leaving it in gives you two layers of backoff multiplying each other, and the outer layer will not respect the server's own guidance. Structured logging hooks let you attach request and response detail to your existing logging setup instead of parsing it back out of log strings.

## Order of work

1. Pin to 2.9 and run the test suite with deprecation warnings surfaced.
2. Fix the constructor, timeout, and attribute-access warnings, which are mechanical.
3. Rewrite `fetch_all()` call sites, which need judgement about memory and reuse.
4. Get a clean run under `-W error::DeprecationWarning`.
5. Bump the interpreter to 3.10 or later if you are not there already.
6. Move to 3.0 and remove any 429 retry logic you were carrying yourself.