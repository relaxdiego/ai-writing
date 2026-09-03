# Migrating from v2 to v3

v3 is a breaking release. There is no codemod, but the changes are mechanical, and there's a supported path that turns most of the work into "fix the warnings."

**Take it in two hops:** upgrade to **2.9** first. That release still behaves like v2 but emits a `DeprecationWarning` for every construct v3 removes. Fix warnings until the run is clean, then bump to v3. Going straight to v3 works too, but you'll find the same problems as runtime failures in production instead of as warnings in CI.

---

## Before you start: Python 3.10

v3 drops Python 3.8; the minimum is 3.10. Do this first — it gates everything else, it's the change most likely to involve other people (base images, CI matrices, other dependencies), and it's the one you can't work around in your own code.

If you're stuck on 3.8, stop here. v2.9 still supports it, so you can land the deprecation fixes now and do the interpreter upgrade separately.

## Step 1: move to 2.9 and turn on warnings

```
pip install 'thelib~=2.9'
```

Then make the warnings visible. They're silent by default in most setups:

```bash
python -W error::DeprecationWarning -m pytest
```

Or, if failing the whole suite at once is too aggressive, start with `-W default::DeprecationWarning` and grep the output.

A caveat worth planning around: warnings only fire on code that actually runs. Test coverage of your call sites is your coverage of this migration. Before you trust a clean run, check that the paths touching this library — especially error handling and pagination — are exercised.

---

## The breaking changes

### 1. Client construction takes a config object

```python
# v2
client = Client("https://api.example.com", "tok_123")

# v3
client = Client(ClientConfig.from_url("https://api.example.com", "tok_123"))
```

`from_url` covers the simple case and is the direct replacement. Build a `ClientConfig` yourself when you need to set anything else (see timeouts, below).

This is the easiest change to find — usually a handful of sites — so do it first and get a win.

### 2. Methods return dataclasses, not dicts

```python
# v2
result = client.get_page()
for item in result["items"]:
    print(item["name"])

# v3
result = client.get_page()
for item in result.items:
    print(item.name)
```

This is the largest change by volume and the one that hides. Watch for dict idioms beyond `[...]` subscripting — a search for square brackets won't find these:

| v2 | v3 |
|---|---|
| `result.get("items", [])` | `result.items` (the field always exists; check for `None` if it's optional) |
| `"items" in result` | `hasattr(result, "items")`, or just access it |
| `for key in result:` | `dataclasses.fields(result)` |
| `{**result, "extra": 1}` | `dataclasses.replace(result, ...)` |
| `json.dumps(result)` | `json.dumps(dataclasses.asdict(result))` |

The serialization case is the one that bites hardest, because it typically surfaces in logging or caching code that isn't well covered by tests. If you write results to a cache, a queue, or a log line, audit those paths by hand rather than relying on the warnings.

The upside: your type checker now understands these results. A `mypy` or `pyright` run after the upgrade will find misspelled field names that used to be silent `KeyError`s at 3am.

### 3. `fetch_all()` is gone; use `iterate()`

`fetch_all()` loaded every result into memory. `iterate()` yields pages instead.

```python
# v2
items = client.fetch_all()
for item in items:
    process(item)

# v3
for page in client.iterate():
    for item in page.items:
        process(item)
```

If you'd rather keep a flat loop, flatten the stream instead of the list:

```python
from itertools import chain

for item in chain.from_iterable(page.items for page in client.iterate()):
    process(item)
```

Resist the temptation to write `items = [i for p in client.iterate() for i in p.items]` as a one-line port. It compiles, it passes tests against your small fixtures, and it reintroduces exactly the memory behaviour the removal was meant to fix. It's justified only where you genuinely need the whole set at once — `len()`, a global sort, a random-access index — and in those cases it's worth a comment saying so.

### 4. Timeouts are objects, with separate connect and read values

```python
# v2
client = Client(url, token, timeout=30.0)

# v3
config = ClientConfig.from_url(url, token)
config.timeout = Timeout(connect=5.0, read=30.0)
client = Client(config)
```

In v3 a float raises `TypeError` — it does not warn, and it does not coerce. v2.9 warns, which is why finding these before the bump matters.

Splitting the value is a judgement call, not a mechanical translation. Your old single number was doing two jobs. A connect timeout should be short (a few seconds — establishing a TCP connection either works quickly or won't work), while a read timeout should cover the slowest response you're willing to wait for. Carrying `30.0` into both fields is the safest literal port, but it means a dead host now ties up a worker for 30 seconds instead of failing fast.

---

## Step 2: move to v3

Once the 2.9 run is warning-free:

```
pip install 'thelib~=3.0'
```

Then run the suite again — this time without the `-W` flag, since the warnings are now errors by construction. Anything that still breaks is code the warnings couldn't reach, which is your signal about where the coverage gaps are.

## What you get

Three additions, none of which require changes to migrate:

- **`AsyncClient`** — same surface as `Client`, awaitable. Adopt it where it helps; the sync client isn't going anywhere.
- **Automatic retry on 429**, honouring `Retry-After`. If you wrote your own rate-limit backoff around v2, this is a good moment to delete it — two retry layers stacked on each other multiply your worst-case latency.
- **Structured logging hooks**, for wiring request/response events into your existing logging setup.

## Checklist

- [ ] Running on Python 3.10+
- [ ] Pinned to 2.9, deprecation warnings surfaced in CI
- [ ] `Client(url, token)` → `Client(ClientConfig.from_url(...))`
- [ ] Key access → attribute access, including `.get()`, `in`, unpacking, and serialization
- [ ] `fetch_all()` → `iterate()`, without rebuilding the full list
- [ ] Float timeouts → `Timeout(connect=..., read=...)`, with values chosen per field
- [ ] Warning-free run on 2.9
- [ ] Custom 429 backoff removed
- [ ] Bumped to 3.x, suite green, type checker run