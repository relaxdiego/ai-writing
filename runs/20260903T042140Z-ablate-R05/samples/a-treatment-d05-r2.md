# Migrating from v2 to v3

v3 changes the shape of the client's public surface in five ways, and there is no codemod. The maintainers recommend upgrading in two hops rather than one: pin to 2.9 first, which still runs your existing code but emits a `DeprecationWarning` for every construct listed below, fix the warnings until the run is clean, then bump to 3.0. The advantage is that 2.9 tells you where your call sites are, which saves you grepping for patterns like `result["items"]` that a search cannot reliably distinguish from ordinary dict access elsewhere in your code.

To make the warnings impossible to ignore while you work through them, run your suite under `python -W error::DeprecationWarning`, or add `filterwarnings = ["error::DeprecationWarning"]` to your pytest config. Turn that back off before you ship 2.9 to production if anything in your dependency tree emits warnings of its own.

## Constructing the client

The two positional arguments are gone; the constructor now takes a single config object.

```python
# v2
client = Client("https://api.example.com", token)

# v3
from mylib import Client, ClientConfig
client = Client(ClientConfig.from_url("https://api.example.com", token))
```

`ClientConfig.from_url` covers the simple case and is the mechanical replacement. If you were passing anything beyond URL and token, or if you build clients in more than two or three places, construct the config once at the edge of your application and pass it down, since that is the arrangement the new API is designed for.

## Dict returns become dataclasses

Every method that returned a `dict` now returns a typed dataclass, so key access becomes attribute access: `result["items"]` is `result.items`. This is the change with the widest blast radius, and it breaks in more ways than the obvious one. Calls to `.get("key")` with a default no longer work; use `getattr` if the field is genuinely optional, though in most cases the dataclass field exists and is `None`. Membership tests like `"items" in result` will fail, as will `**result` unpacking and passing the result straight to `json.dumps`. Where you were serializing a response, insert an explicit conversion at that boundary:

```python
import dataclasses
payload = json.dumps(dataclasses.asdict(result))
```

The upside is that a type checker can now find the rest of these for you. If you run mypy or pyright, do it after this step rather than before; the errors it reports at that point are close to a complete list of the remaining call sites.

## `fetch_all()` is removed

`fetch_all()` loaded the entire result set into memory, which is why it is gone rather than deprecated in place. `iterate()` replaces it and yields pages, not individual records, so the rewrite adds a level of nesting:

```python
# v2
for item in client.fetch_all():
    process(item)

# v3
for page in client.iterate():
    for item in page.items:
        process(item)
```

If you prefer to keep the flat loop, `itertools.chain.from_iterable(page.items for page in client.iterate())` gives you an iterator of items. What you should not do is `[item for page in client.iterate() for item in page.items]` as a reflex, since materializing the list reintroduces exactly the memory behaviour the removal was meant to fix. Code that genuinely needs the whole set at once, such as a sort across all results, is worth looking at again; often the aggregate can be computed incrementally as pages arrive.

## Timeouts

A float is no longer accepted, and v3 raises `TypeError` rather than warning, so anything you miss fails loudly at the call site.

```python
# v2
client.request(..., timeout=5.0)

# v3
from mylib import Timeout
client.request(..., timeout=Timeout(connect=5.0, read=5.0))
```

Setting both values to your old float is the safe starting point, but note that it is not an exact translation: the single float and the pair do not budget time the same way, so a request that previously fit inside the old limit can now take longer in the worst case. If you have latency budgets that depend on the timeout, treat this as a chance to set them deliberately, with a short connect timeout and a longer read timeout being the usual arrangement.

## Python 3.10 minimum

Support for 3.8 is dropped. Update `requires-python` in your packaging metadata and drop 3.8 and 3.9 from your CI matrix before you bump the library, so you find out about the runtime change separately from the API changes. Nothing in the migration requires new syntax, so you can do the interpreter bump as its own commit.

## What you get in v3

Three additions need no changes on your side, but two of them may let you delete code. Retries on 429 are now automatic and honour `Retry-After`, so if you hand-rolled a retry loop around rate limiting, remove it rather than leaving it in place; two layers of backoff will multiply your wait times and make throttling look like a hang. Structured logging hooks replace whatever you were doing to correlate requests, and are worth wiring up while you are already touching the client construction code. `AsyncClient` mirrors the sync API method for method, so an async port is largely mechanical, though it is a separate piece of work and not something to attempt in the same pass as the migration.

## Suggested order

Working through it in this sequence keeps each step verifiable. Bump the interpreter and CI matrix first, then pin 2.9 and turn deprecation warnings into errors. Fix the constructor and timeout call sites, which are mechanical and few. Then take the dict-to-dataclass conversion, leaning on a type checker once the first pass is done. Save `fetch_all()` for last, because it is the only change that may need a real decision about how your code consumes results. When the suite is clean under 2.9 with warnings as errors, moving the pin to 3.0 should be uneventful.