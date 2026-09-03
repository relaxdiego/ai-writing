# Migrating from v2 to v3

Version 3 changes five things that will break existing code: the constructor signature, the return types of every method, the removal of `fetch_all()`, the timeout representation, and the minimum Python version. None of them can be fixed automatically, and no codemod exists, so the work is manual. The maintainers recommend routing through v2.9 rather than jumping straight across, because v2.9 ships deprecation warnings for all five and will find your call sites for you.

## Go through 2.9 first

Pin to `2.9`, then run your test suite with deprecation warnings promoted to errors:

```
pip install 'yourlib==2.9'
python -W error::DeprecationWarning -m pytest
```

Every construct removed in v3 warns here, and the warning fires at the call site rather than inside the library, which matters most for the dict-to-dataclass change: key access on a result is nearly impossible to find by grep once results have been passed through a few layers of your own code, but a warning at the moment of subscripting points straight at the line. Fix until the suite is clean under `-W error`, ship that, and let it run in production for a release cycle if you can. Only then bump to v3, where the same mistakes raise instead of warn.

## Python 3.10 minimum

Support for 3.8 is gone and 3.10 is the floor, so settle this before touching any library code. If you are on 3.8 you also need to clear 3.9 on the way, and the interpreter upgrade is likely to surface unrelated dependency pins. Doing it as a separate commit keeps the two failure modes distinguishable.

## Constructing a client

The two positional arguments are replaced by a single config object:

```python
# v2
client = Client("https://api.example.com", "tok_abc")

# v3
client = Client(ClientConfig.from_url("https://api.example.com", "tok_abc"))
```

For most call sites `from_url` is a mechanical substitution. It is worth pausing on the ones where the URL or token is assembled conditionally, because those are usually the places where a real `ClientConfig` built field by field reads better than a helper that exists to paper over the simple case. The same config object is accepted by `AsyncClient`, so anything you factor out here is reusable if you later go async.

## Results are dataclasses

Methods that returned `dict` now return typed dataclasses, and attribute access replaces key access throughout:

```python
# v2
for item in result["items"]:
    print(item["name"])

# v3
for item in result.items:
    print(item.name)
```

Two consequences are easy to miss. Code that serialises results directly, passing them to `json.dumps` or into a template that expects a mapping, will no longer work; use `dataclasses.asdict(result)` at the boundary where you actually need a dict, not everywhere. And `result.get("field")` had been returning `None` for absent keys, silently; the dataclass declares optional fields explicitly, so a genuine optional is still `None` but a misspelled or removed field now raises `AttributeError`. Any spot where you were relying on `.get()` to swallow a name you were not sure about deserves a look rather than a blind rewrite to `getattr(result, "field", None)`.

## `fetch_all()` is gone

`fetch_all()` loaded the entire result set into memory, which is why it was removed rather than deprecated in place. `iterate()` yields pages, so the natural rewrite pushes your processing into the loop:

```python
# v2
for item in client.fetch_all(query):
    process(item)

# v3
for page in client.iterate(query):
    for item in page.items:
        process(item)
```

You can restore the old shape with `list(chain.from_iterable(p.items for p in client.iterate(query)))`, and for a query you know returns fifty rows that is a reasonable thing to write. Reaching for it everywhere reintroduces exactly the problem the removal was meant to solve, so treat it as a deliberate choice at each site rather than a find-and-replace.

## Timeouts

A float is no longer accepted and passing one raises `TypeError` rather than warning:

```python
# v2
client.fetch(query, timeout=5.0)

# v3
client.fetch(query, timeout=Timeout(connect=5.0, read=5.0))
```

The translation is not quite value-preserving. The old float bounded the operation as a whole, whereas connect and read are budgeted separately, so the literal transcription above roughly doubles the worst-case wall clock. Where a timeout was chosen to satisfy an external deadline, split the original budget instead of duplicating it, and give connect the smaller share: a connection that has not been established in a second or two is not going to be.

## What you gain

Three additions arrive with v3 and none of them require changes on your side. `AsyncClient` mirrors the sync API and takes the same `ClientConfig`. Requests that return 429 are retried automatically with `Retry-After` honoured, which removes whatever backoff wrapper you had built around the client; delete it, because two layers of retry compound multiplicatively. Note that automatic retry can extend the total wall clock of a call well past what your old timeout implied, so if you have an outer deadline, set it against retry behaviour rather than against the per-request timeout alone. Structured logging hooks replace log scraping if you were doing any.

## Suggested order

Take the interpreter upgrade first and land it alone. Then move to 2.9 and work the warnings, starting with the constructor because it is the smallest change and touches the fewest files, then the timeouts, then the result access, which is the long tail. Leave `fetch_all()` for last, since it is the one change that asks you to restructure code rather than rewrite an expression, and you want the rest of the suite green while you do it. Bumping to v3 afterwards should be a version pin and nothing else.