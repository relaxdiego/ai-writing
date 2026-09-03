# Upgrading from v2 to v3

Version 3 is a rewrite of the public surface rather than a set of tweaks, so the useful mental model is that you are changing four things: how a client is constructed, how results are read, how large result sets are consumed, and how timeouts are expressed. There is no codemod. The path the maintainers recommend, and the one this guide follows, is to land on v2.9 first, let its deprecation warnings enumerate your call sites, fix them there while the old behaviour still works, and only then bump to v3. Doing it in one jump is possible but means debugging construction errors, attribute errors and `TypeError`s at the same time, with no running intermediate state to compare against.

## Before you start: Python 3.10

v3 drops Python 3.8; the minimum is 3.10. This is a hard gate rather than a migration step, because no amount of call-site fixing will make v3 install on an older interpreter. If your project is still on 3.8 or 3.9, upgrade the interpreter first and get your test suite green on it, then begin the library migration. Keeping the two moves separate matters: a test failure after a combined jump could belong to either change, and you will spend longer bisecting than you saved.

## Step one: pin v2.9 and surface the warnings

Pin to `>=2.9,<3` and run your test suite with deprecation warnings escalated to errors:

```
python -W error::DeprecationWarning -m pytest
```

Each failure now points at a line that will break under v3. Work through them with the sections below. The value of this step is that it finds call sites your grep would miss, particularly dictionary access on results that gets passed through a helper before anyone subscripts it, and it lets you verify each fix against v2.9's still-working runtime instead of against a broken v3 import.

## Client construction

`Client(url, token)` becomes `Client(config)`, where the config carries what used to be positional arguments plus the new settings for retry and logging.

```python
# v2
client = Client("https://api.example.com", token)

# v3
from mylib import Client, ClientConfig
client = Client(ClientConfig.from_url("https://api.example.com", token))
```

`ClientConfig.from_url` exists precisely so the common case stays a one-liner, and for most applications that is the whole change. Construct `ClientConfig` directly only when you need the settings that had no v2 equivalent, such as adjusting retry behaviour or attaching a logging hook. If you build clients in more than two or three places, this is a good moment to introduce a single factory function that returns a configured client, so the next construction change touches one line.

## Results are dataclasses, not dicts

Every method that returned a `dict` now returns a typed dataclass, and key access becomes attribute access:

```python
# v2
items = result["items"]
cursor = result.get("next_cursor")

# v3
items = result.items
cursor = result.next_cursor
```

Two consequences are easy to miss. First, `.get()` with a default has no direct replacement, because a dataclass field is either declared or absent; a field that may be unset will be `None` rather than missing, so `result.next_cursor or fallback` usually replaces `result.get("next_cursor", fallback)`. Second, anything that treated a result as a plain dict now fails: `json.dumps(result)`, `**result`, `result.keys()`, and mock objects in your tests that returned dicts. Use `dataclasses.asdict(result)` at the boundary where you genuinely need a mapping, such as serialising to a queue or a log line, and leave the rest of your code working on attributes where the type checker can see it. If you run mypy or pyright, this change is where the upgrade pays for itself, so it is worth enabling type checking on the modules that touch results before you move on.

## `fetch_all()` is gone

`fetch_all()` was removed because it accumulated the entire result set in memory before returning. `iterate()` replaces it and yields pages:

```python
# v2
for item in client.fetch_all():
    process(item)

# v3
for page in client.iterate():
    for item in page.items:
        process(item)
```

The nested loop flattens neatly with `itertools.chain.from_iterable(page.items for page in client.iterate())` if a single loop reads better at the call site. You can also reconstruct the old behaviour with a list comprehension over the pages, and that is a legitimate short-term move for a script that already fits in memory, but it reintroduces exactly the problem the removal was meant to solve. Anywhere the result set grows with your data, take the streaming form now. The attribute holding a page's rows follows the page dataclass definition in the release notes; `page.items` is the shape shown there.

## Timeouts

A float is no longer accepted, and v3 raises `TypeError` rather than warning:

```python
# v2
client.get(path, timeout=30.0)

# v3
from mylib import Timeout
client.get(path, timeout=Timeout(connect=5.0, read=30.0))
```

Splitting connect from read means there is no mechanical translation of your old value, so you have to make a judgement per call site. The translation that preserves observed behaviour in the ordinary case is to keep your old number as `read` and set a small `connect`, on the assumption that connections to a healthy endpoint establish in well under a second and your old float was really governing how long you waited for the response body. Where that assumption does not hold, for instance calls to an endpoint that is slow to accept connections under load, set `connect` deliberately. Note that the worst case is now the sum rather than the single old bound, which matters if a caller upstream has its own deadline.

## What you get in return

Three additions need no changes to adopt, but two of them change runtime behaviour enough to be worth knowing about before you deploy.

Retry on 429 is automatic and honours `Retry-After`. If you wrote your own retry-and-backoff wrapper around this client, remove it during the migration; leaving both in place multiplies the delays and can turn a brief rate limit into a request that appears to hang. Any test that asserts a 429 propagates as an exception will also need rewriting, since the client now waits and retries instead.

`AsyncClient` accepts the same `ClientConfig` and mirrors the sync API, so a service that is already async can drop the thread pool it was using to keep this client off the event loop. Structured logging hooks let you attach request and response metadata to your own logger rather than parsing the library's log output, which is the cleanest way to get retry activity into your metrics.

## Step two: bump to v3

Once v2.9 runs clean under `-W error::DeprecationWarning`, change the pin to `>=3,<4` and run the suite again. What surfaces here is the residue the warnings could not catch: reflective code that built keys as strings, test doubles returning dicts, and float timeouts on paths your tests never exercised. The float timeout is the one to watch in production, because it fails loudly at call time rather than at import, so a rarely-taken branch can carry a `TypeError` past a green test run. A grep for `timeout=` across the codebase before you deploy is a cheap way to close that gap.