# Migrating from v2 to v3

v3 breaks five things: the client constructor, the return types of every method, the `fetch_all` helper, the timeout argument, and support for Python 3.8 and 3.9. There is no codemod, so the upgrade is a manual pass over your call sites, and the intermediate release v2.9 exists to make that pass mechanical rather than exploratory. v2.9 is API-compatible with v2 but emits a `DeprecationWarning` at every site v3 will break, so the recommended path is to pin v2.9 first, promote deprecation warnings to errors in your test suite, work through the failures, and only then bump the pin to v3. Every fix you make under v2.9 is valid under both versions, which means you can ship the intermediate state to production in normal-sized changes instead of maintaining a long-lived migration branch.

To surface the warnings, run your suite with `-W error::DeprecationWarning`, or add `filterwarnings = ["error::DeprecationWarning"]` to your pytest configuration. Warnings only fire on code paths that execute, so coverage of your integration boundary matters more here than usual; if a rarely-taken branch calls `fetch_all`, v2.9 will not tell you about it, and v3 will fail at runtime rather than at import.

## The interpreter first

v3 requires Python 3.10 or later. v2.9 still runs on 3.8 and 3.9 and warns at import when it does, so the runtime bump and the code changes can be separated: move your interpreter to 3.10 while still on v2.9, deploy that alone, and keep the two classes of failure from arriving in the same change. Nothing else in this guide depends on the interpreter version, so if your deployment environment makes the runtime bump slow, you can begin the code changes in parallel and merge them in any order.

## Constructing the client

The two positional arguments are gone, replaced by a single configuration object:

```python
# v2
client = Client("https://api.example.com", "tok_123")

# v3
from mylib import Client, ClientConfig
client = Client(ClientConfig.from_url("https://api.example.com", "tok_123"))
```

`ClientConfig.from_url` exists precisely so that the common case stays one line, and for most codebases the change is a mechanical rewrite at the handful of places a client is built. If you were passing other keyword arguments to `Client`, they now belong on the config object rather than the constructor, which is also where the new timeout, retry, and logging settings live. Building the config separately from the client is worth doing where you construct clients in more than one place, since the config is an ordinary value you can define once in a settings module and reuse.

## Timeouts

A float is no longer accepted, and passing one raises `TypeError` immediately rather than warning:

```python
# v2
client = Client(url, token, timeout=30.0)

# v3
from mylib import Timeout
config = ClientConfig.from_url(url, token, timeout=Timeout(connect=5.0, read=30.0))
```

The translation is not quite arithmetic. In v2 a single float bounded the whole operation, whereas `connect` and `read` bound two phases that run in sequence, so `Timeout(connect=30.0, read=30.0)` permits up to sixty seconds of wall clock where `timeout=30.0` permitted thirty. Pick a connect timeout that reflects how long a healthy TCP handshake and TLS negotiation take against your endpoint, which is usually a few seconds at most, and give the remaining budget to `read`. If you have alerting tuned to the old end-to-end bound, recompute it as the sum rather than carrying the old number across.

## Return types

Methods that returned `dict` now return dataclasses, so key access becomes attribute access:

```python
# v2
page = client.list_items(cursor=None)
for item in page["items"]:
    print(item["name"])

# v3
page = client.list_items(cursor=None)
for item in page.items:
    print(item.name)
```

This is the change that touches the most lines, and the subscript rewrite is only the visible part of it. Anything else you were doing to those dicts stops working too: `page.get("next_cursor")` has no equivalent, because a dataclass field is always present and holds `None` when empty, so the guarded lookup becomes a plain `page.next_cursor`. Membership tests like `"next_cursor" in page` are now static facts about the type rather than runtime questions and should be deleted. Splatting a result into a function call with `**page` fails, and so does passing one straight to `json.dumps`; for serialisation, use `dataclasses.asdict(page)`, which reproduces the old shape closely enough for most logging and caching code. Because the fields are typed, running mypy or pyright over the migrated code will find the sites that v2.9's warnings could not reach, and it is worth doing that pass even if you do not otherwise type-check the project.

## `fetch_all` is gone

`fetch_all` loaded every page into a single list, which is why it was removed rather than renamed. `iterate` yields pages instead:

```python
# v2
for item in client.fetch_all(query):
    process(item)

# v3
for page in client.iterate(query):
    for item in page.items:
        process(item)
```

The literal replacement, `[item for page in client.iterate(query) for item in page.items]`, reproduces the old memory behaviour and defeats the purpose of the change, so treat any call site where you reach for it as one that needs a second look. Where the accumulated list fed an aggregate, compute the aggregate incrementally as pages arrive. Where it fed a bulk write, write per page and let the database do the accumulating. The cases that genuinely need the whole set in memory are usually small and bounded, and there the comprehension is fine as long as you know the bound.

## What you get in return

Three additions require no changes to adopt. `AsyncClient` mirrors the synchronous API with `await` and `async for`, taking the same `ClientConfig`. Retries on HTTP 429 are now automatic and honour the `Retry-After` header, so if you wrote your own rate-limit backoff around v2 calls, remove it rather than stacking it on top of the built-in behaviour and doubling your wait times. Structured logging hooks are configured on `ClientConfig` and emit request and response events as records rather than formatted strings, which is the supported way to get at retry and timing information now that the timing is no longer under your control.

Sequencing the whole thing: bump the interpreter on v2.9, then fix the constructor and timeout warnings, which are localised, then the return-type warnings, which are diffuse but mechanical, and leave `fetch_all` for last because it is the only one that asks you to change how the surrounding code is shaped.