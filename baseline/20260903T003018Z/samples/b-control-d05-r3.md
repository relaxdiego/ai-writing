# Migrating from v2 to v3

## Before you start

There is no codemod for this upgrade. Every breaking change below has to be found and fixed by hand, so the maintainers recommend a two-step path:

1. **Upgrade to v2.9 first.** It is API-compatible with v2.x but emits `DeprecationWarning` for every pattern that breaks in v3.
2. **Fix all the warnings under v2.9**, where your test suite still passes and the old code still runs.
3. **Then upgrade to v3**, which turns those warnings into errors.

Run your suite with warnings visible so they aren't swallowed:

```bash
python -W error::DeprecationWarning -m pytest
```

Or, to see them without failing:

```bash
python -W default::DeprecationWarning -m pytest
```

The one thing v2.9 cannot warn you about is Python version support — check that first.

---

## 1. Python 3.10 minimum

Python 3.8 is no longer supported. Upgrade your interpreter before anything else; if you are pinned to 3.8, stop here and resolve that first.

```toml
# pyproject.toml
requires-python = ">=3.10"
```

Also update your CI matrix and any Docker base images. If you drop 3.9 in the same pass, you can start using `X | None` syntax in annotations, `match` statements, and parenthesized context managers.

---

## 2. Client construction takes a config object

`Client(url, token)` is gone.

```python
# v2
client = Client("https://api.example.com", "tok_123")

# v3 — simple case
client = Client(ClientConfig.from_url("https://api.example.com", "tok_123"))

# v3 — when you need more than url + token
client = Client(ClientConfig(
    url="https://api.example.com",
    token="tok_123",
    timeout=Timeout(connect=3.0, read=30.0),
))
```

`ClientConfig.from_url()` exists precisely so the common case stays a one-liner. Reach for the full constructor only when you're setting timeouts, retries, or logging hooks.

If you construct clients in many places, this is a good moment to centralize: build the config once at startup and pass it around, rather than threading a URL and token through your call sites.

---

## 3. Return values are dataclasses, not dicts

Every method that returned a `dict` now returns a typed dataclass. Key access becomes attribute access.

```python
# v2
result = client.get_items()
for item in result["items"]:
    print(item["name"])

# v3
result = client.get_items()
for item in result.items:
    print(item.name)
```

Watch for the less obvious consequences:

| v2 pattern | v3 equivalent |
|---|---|
| `result["items"]` | `result.items` |
| `result.get("cursor")` | `result.cursor` (typed; `None` if absent) |
| `"cursor" in result` | `result.cursor is not None` |
| `json.dumps(result)` | `json.dumps(dataclasses.asdict(result))` |
| `dict(result)` | `dataclasses.asdict(result)` |
| `result.keys()` / `.items()` | `dataclasses.fields(result)` |
| `result["new_field"] = x` | construct a new instance, or `dataclasses.replace(result, ...)` |

Two failure modes worth calling out:

- **Serialization.** Code that passed responses straight into `json.dumps`, a cache, or a message queue will now raise `TypeError`. Use `dataclasses.asdict()` at the boundary.
- **Mutation.** Dataclass instances are not dicts; you cannot stuff extra keys onto a response. Where you were decorating responses with local metadata, use your own wrapper type or `dataclasses.replace()`.

The upside: your type checker now catches typos that used to be `KeyError` at runtime. Running `mypy` or `pyright` after this step will find remaining dict-style access for you faster than grepping will.

---

## 4. `fetch_all()` is removed — use `iterate()`

`fetch_all()` loaded the entire result set into memory, which is why it's gone. `iterate()` yields pages.

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

Note that `iterate()` yields **pages**, not individual items. If you want a flat stream:

```python
from itertools import chain

for item in chain.from_iterable(page.items for page in client.iterate()):
    process(item)
```

If you genuinely need the whole set in memory — a small, bounded collection you're about to sort or index — do it explicitly so the cost is visible at the call site:

```python
items = [item for page in client.iterate() for item in page.items]
```

Places where `fetch_all()` was followed by `len()`, a sort, or a slice deserve a second look: those are often the spots where streaming would be a real improvement rather than a mechanical rewrite.

---

## 5. Timeouts are a `Timeout` object

Floats are no longer accepted. In v2.9 passing one warns; in v3 it raises `TypeError`.

```python
# v2
client = Client(url, token, timeout=30.0)

# v3
config = ClientConfig(
    url=url,
    token=token,
    timeout=Timeout(connect=5.0, read=30.0),
)
```

The split is deliberate: a single value conflated "how long to wait for a connection" with "how long to wait for data." Connect timeouts should generally be short (a few seconds — a healthy server accepts immediately), while read timeouts should reflect how long the operation legitimately takes.

Mechanically translating `timeout=30.0` into `Timeout(connect=30.0, read=30.0)` works, but it preserves a 30-second connect timeout you almost certainly don't want. Prefer a short connect value and carry your old number over as the read timeout.

Because this raises rather than warns, any timeout you set on a rarely-exercised path will fail at runtime rather than at import. Grep for `timeout=` across the codebase rather than relying solely on tests.

---

## What you get in v3

None of these require changes, but they may let you delete code:

**`AsyncClient`** — same API surface, async. Useful if you were running the sync client in a thread pool:

```python
async with AsyncClient(config) as client:
    async for page in client.iterate():
        ...
```

**Automatic retry on 429** with `Retry-After` honoured. If you hand-rolled rate-limit backoff around v2 calls, you can likely remove it — check that your wrapper isn't now retrying on top of the built-in retry, which would multiply your backoff.

**Structured logging hooks** — configured on `ClientConfig`, replacing whatever request/response logging you wrapped around call sites.

---

## Suggested order of work

1. Move to Python 3.10+; get CI green.
2. Upgrade to v2.9. Turn on `DeprecationWarning`.
3. Fix construction sites (`ClientConfig`), then timeouts, then `fetch_all()`, then dict access.
4. Run a type checker — it catches the residual attribute-access misses.
5. Confirm zero deprecation warnings.
6. Upgrade to v3. Remove any now-redundant retry logic.

Doing dict access last is intentional: it's the largest and most mechanical change, and it's much easier once the call sites have stopped moving.