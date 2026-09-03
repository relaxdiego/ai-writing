No file tools are available in this session, so here's the guide as markdown — ready to drop into `docs/migrating-v2-to-v3.md`.

---

# Migrating from v2 to v3

v3 is a typed, streaming-friendly rewrite of the client surface. Five things break; the rest is additive.

There is **no codemod**. The supported path is two hops:

```
v2.x  →  v2.9  (fix deprecation warnings)  →  v3.0
```

v2.9 warns on every construct v3 removes. If you land on v2.9 with a warning-free test suite, the v3 bump is usually a one-line dependency change.

## At a glance

| v2 | v3 |
|---|---|
| `Client(url, token)` | `Client(ClientConfig.from_url(url, token))` |
| `result["items"]` | `result.items` |
| `client.fetch_all()` | `client.iterate()` (yields pages) |
| `timeout=30.0` | `timeout=Timeout(connect=5.0, read=30.0)` |
| Python 3.8+ | Python 3.10+ |

New and optional: `AsyncClient`, automatic 429 retry, structured logging hooks.

## Step 0: Python 3.10

v3 requires **Python 3.10 or newer**. 3.8 and 3.9 are unsupported.

Do this first. It gates everything else, it is usually the longest pole, and it is independent of the library — you can ship the interpreter upgrade on its own and let it soak before touching any client code.

## Step 1: Move to v2.9 and turn warnings into errors

```
pip install 'yourlib>=2.9,<3'
```

v2.9 is API-compatible with v2.x. It emits `DeprecationWarning` for all five breaking changes below.

Deprecation warnings are hidden by default, so make them loud:

```bash
python -W error::DeprecationWarning -m pytest
```

or, in `pyproject.toml`:

```toml
[tool.pytest.ini_options]
filterwarnings = [
    "error::DeprecationWarning:yourlib.*",
]
```

Fix everything that fires. Then bump to `>=3,<4` — most of the work is already done.

Warnings only cover code paths your tests actually execute. Coverage gaps are the usual source of post-upgrade surprises, so treat a warning-free run as necessary, not sufficient. The type-checker pass in Step 3 covers what the tests miss.

## Step 2: Construct the client from a config object

The two-positional-argument constructor is gone. Configuration is now one object.

```python
# v2
client = Client("https://api.example.com", token)

# v3 — simple case
from yourlib import Client, ClientConfig

client = Client(ClientConfig.from_url("https://api.example.com", token))
```

`from_url` is a convenience shim for exactly this case. If you set anything else — timeouts, retries, logging hooks — build the config directly:

```python
config = ClientConfig(
    url="https://api.example.com",
    token=token,
    timeout=Timeout(connect=5.0, read=30.0),
)
client = Client(config)
```

If you build clients in more than two or three places, add a factory now and migrate the call sites to it. That way any future config change is one edit:

```python
def make_client() -> Client:
    return Client(ClientConfig.from_url(settings.api_url, settings.api_token))
```

## Step 3: Attribute access replaces key access

Every method that returned `dict` now returns a typed dataclass.

```python
# v2
result = client.search("query")
for item in result["items"]:
    print(item["name"])

# v3
result = client.search("query")
for item in result.items:
    print(item.name)
```

This is the widest-reaching change, and it has three traps.

**`.items` is now an attribute, not a dict method.** Code that iterated the mapping breaks in a way that reads oddly:

```python
for key, value in result.items():   # v2: dict.items()
    ...
# v3: TypeError: 'list' object is not callable
```

**`.get()` is gone.** There is no default-value lookup, because the fields are statically known. A field that may be absent is typed `Optional` and is `None`:

```python
# v2
cursor = result.get("next_cursor", None)

# v3
cursor = result.next_cursor          # None when absent
```

**Serialization needs an explicit conversion.** Anything that passed a result to `json.dumps`, `**kwargs`-unpacked it, or stuffed it in a cache expecting a mapping now needs:

```python
from dataclasses import asdict

json.dumps(asdict(result))
```

The payoff: a type checker now finds the rest of this for you. Run it before you ship — it catches the untested branches that Step 1 could not.

```bash
mypy src/    # or: pyright src/
```

## Step 4: Replace `fetch_all()` with `iterate()`

`fetch_all()` is removed. It accumulated every page into one list, so peak memory scaled with the result set — the reason it's gone.

`iterate()` **yields pages, not records.** This is the easiest thing to get wrong:

```python
# v2
for item in client.fetch_all():
    process(item)

# v3
for page in client.iterate():
    for item in page.items:
        process(item)
```

If you want a flat stream of records, flatten explicitly:

```python
from itertools import chain

items = chain.from_iterable(page.items for page in client.iterate())
for item in items:
    process(item)
```

If some call site genuinely needs the whole set in memory — a small result you sort, or a length check — you can reproduce the old behaviour in one line:

```python
all_items = [item for page in client.iterate() for item in page.items]
```

That is a legitimate escape hatch for small, bounded result sets. Use it deliberately rather than as a blanket find-and-replace: applying it everywhere reintroduces exactly the memory profile v3 removed, and the streaming form is usually a smaller diff than it looks.

## Step 5: Timeouts are objects, not floats

Timeouts split into separate connect and read values.

```python
# v2
client = Client(url, token, timeout=30.0)

# v3
from yourlib import Timeout

config = ClientConfig.from_url(url, token)
config.timeout = Timeout(connect=5.0, read=30.0)
```

Per-call overrides take the same object:

```python
result = client.search("query", timeout=Timeout(connect=2.0, read=10.0))
```

**A bare float raises `TypeError`.** In v2.9 it warns; in v3 it is a hard error, immediately and at every call site. There is no compatibility shim and no coercion.

Pick the new values deliberately. The old single float was not a straight sum of the two new ones, so there is no mechanical translation. A reasonable starting point is to keep your old value as `read` and set a short `connect` (2–5 seconds is typical — a TCP handshake that hasn't completed in five seconds is not going to). Then check the result against your actual latency budget, because worst-case wall time per request is now roughly `connect + read` rather than a single ceiling.

## What's new in v3

None of this is required to complete the migration. Consider it once you're on v3 and green.

**`AsyncClient`.** Same surface, awaitable; `iterate()` becomes an async generator.

```python
from yourlib import AsyncClient, ClientConfig

async with AsyncClient(ClientConfig.from_url(url, token)) as client:
    async for page in client.iterate():
        for item in page.items:
            await process(item)
```

**Automatic retry on 429.** v3 retries rate-limited requests and honours the `Retry-After` header. Two consequences worth checking:

- **Delete your hand-rolled 429 handling.** A retry loop wrapped around a client that already retries multiplies the backoff — and can turn a 30-second stall into minutes.
- **Retries extend wall-clock time beyond `Timeout`.** `Timeout` bounds a single attempt, not the retry sequence. Any caller with its own overall deadline needs to account for that.

**Structured logging hooks.** Request/response lifecycle events are emitted as structured records, so you can wire them into your existing logging pipeline instead of parsing log strings.

## Checklist

- [ ] Running on Python 3.10+
- [ ] Pinned to v2.9, test suite green with `DeprecationWarning` as an error
- [ ] All `Client(url, token)` call sites take a `ClientConfig`
- [ ] All `result["key"]` converted to `result.key`
- [ ] No remaining `.get()` on results; serialization uses `asdict()`
- [ ] No `fetch_all()`; `iterate()` consumers handle **pages**, not records
- [ ] No float timeouts anywhere, including per-call overrides
- [ ] Type checker clean (catches the dict access your tests don't reach)
- [ ] Hand-rolled 429 retry logic removed
- [ ] Pinned to `>=3,<4`

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `TypeError: Client() takes 2 positional arguments` | Old constructor | `Client(ClientConfig.from_url(url, token))` |
| `TypeError: timeout must be a Timeout` | Float timeout | `Timeout(connect=..., read=...)` |
| `TypeError: 'list' object is not callable` | `result.items()` | Drop the parens |
| `AttributeError: no attribute 'get'` | Dict-style lookup | Attribute access; optional fields are `None` |
| `AttributeError: no attribute 'fetch_all'` | Removed | `iterate()`, and flatten if needed |
| Iteration yields pages, not records | `iterate()` is page-wise | Nest the loop or `chain.from_iterable` |
| `TypeError: not JSON serializable` | Dataclass passed to `json.dumps` | `asdict(result)` |
| Requests suddenly much slower | Doubled retry logic | Remove your own 429 loop |

---

Two things I filled in where the brief was silent, in case they don't match the real API: I assumed `timeout` lives on `ClientConfig` with a per-call override keyword, and that pages expose their records as `page.items`. Adjust those names and the rest holds. If you want, I can also draft the v2.9 deprecation-warning messages so they point at the specific replacement for each case.