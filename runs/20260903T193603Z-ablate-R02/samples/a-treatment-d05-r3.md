# Migrating from v2 to v3

v3 changes five things that will break existing code, and adds three that will not. The maintainers recommend upgrading in two hops rather than one: move to v2.9 first, which emits a `DeprecationWarning` for every construct listed below, fix the warnings until the run is clean, then bump to v3. There is no codemod, so the warnings are the closest thing to a checklist you will get.

## Step 0: Python 3.10

v3 drops Python 3.8; the minimum is 3.10. Do this before anything else, because on 3.8 the v3 install will simply fail to resolve and you will be debugging your dependency solver instead of your code.

## Step 1: run on v2.9 with warnings visible

Pin to `>=2.9,<3`. Deprecation warnings are silenced by default outside `__main__`, so you need to ask for them:

```
python -W error::DeprecationWarning -m yourapp
pytest -W error::DeprecationWarning
```

Turning them into errors gives you a stack trace at each call site. If your test suite covers the library surface well, this is the whole migration; work through the failures until the suite is clean, then change the pin to `>=3,<4`.

## Client construction

`Client(url, token)` is replaced by `Client(config: ClientConfig)`. For the common case there is a constructor helper:

```python
# v2
client = Client("https://api.example.com", token)

# v3
client = Client(ClientConfig.from_url("https://api.example.com", token))
```

Anywhere you were passing extra keyword arguments to `Client`, those now belong on the config object instead, which is where the timeout change below lands too.

## Methods return dataclasses, not dicts

Every method that returned a `dict` now returns a typed dataclass, so `result["items"]` becomes `result.items`. The straightforward substitutions are mechanical, but a few habits break less obviously:

- `result.get("items", [])` has no equivalent. The field always exists; if it is optional it will be `None`, so use `result.items or []`.
- `"items" in result` and `for key in result` no longer work. Use `hasattr`, or better, rely on the type.
- `json.dumps(result)` fails. Use `dataclasses.asdict(result)` first.
- `**result` unpacking into another call fails, same fix.

The compensation is that your type checker now catches typos in field names that previously surfaced as a `KeyError` in production.

## `fetch_all()` is removed

`fetch_all()` loaded the entire result set into memory, which is why it is gone rather than deprecated-and-kept. `iterate()` replaces it and yields pages:

```python
# v2
for item in client.fetch_all():
    process(item)

# v3
for page in client.iterate():
    for item in page.items:
        process(item)
```

Note the extra loop: `iterate()` yields pages, not items. If you want a flat stream of items, `itertools.chain.from_iterable(page.items for page in client.iterate())` gives you one without materialising anything.

You can reconstruct the old behaviour with `[item for page in client.iterate() for item in page.items]`, and occasionally that is the right call, when you genuinely need random access to a small result set. Reach for it knowingly rather than as a reflex, since it reintroduces exactly the memory profile the removal was meant to prevent.

## Timeouts

Timeouts were a float in seconds. They are now a `Timeout` object with separate connect and read values, and passing a float raises `TypeError` rather than warning, even in 2.9's deprecation pass:

```python
# v2
client = Client(url, token, timeout=30.0)

# v3
config = ClientConfig.from_url(url, token)
config.timeout = Timeout(connect=5.0, read=30.0)
client = Client(config)
```

The literal translation of `timeout=30.0` is `Timeout(connect=30.0, read=30.0)`, but that is rarely what you want: it allows 30 seconds to establish a connection, which in practice means a dead host stalls you for far longer than the old single value implied. A short connect timeout with a longer read timeout is the usual shape.

## What arrives for free

Three additions need no changes to adopt.

`AsyncClient` mirrors the sync API with the same config object, so the migration above is also the preparation for moving to async later if you want it.

Retries on HTTP 429 are now automatic and honour `Retry-After`. If you built your own backoff wrapper around a v2 client, check whether it is still doing anything useful; two layers of retry multiply rather than add, and the combined delay can be surprising.

Structured logging hooks let you attach a handler and get request metadata as fields rather than parsing log strings.

## Order of work

Bump Python, then move to 2.9 and clear the warnings in this order: client construction first, since it gates everything else; then timeouts, because they surface as hard `TypeError`s and are quick; then `fetch_all()` call sites, which need the most thought; and dict-to-dataclass access last, because it is the broadest change and the one your type checker helps most with once the rest compiles.