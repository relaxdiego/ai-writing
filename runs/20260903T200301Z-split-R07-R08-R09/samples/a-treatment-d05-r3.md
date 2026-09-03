# Upgrading from v2 to v3

Upgrade in two steps. Install v2.9 first, fix every deprecation warning it emits, and only then move to v3. Every breaking change below warns in v2.9 and raises in v3, so the intermediate release turns a large simultaneous port into a series of small changes you can ship and verify one at a time. There is no codemod, and the failure mode of going straight to v3 is a stack of unrelated `TypeError`s and `AttributeError`s appearing at once in code you have not touched in a year.

## At a glance

| Change | v2 | v3 |
| --- | --- | --- |
| Construction | `Client(url, token)` | `Client(ClientConfig.from_url(url, token))` |
| Return values | `result["items"]` | `result.items` |
| Full result set | `client.fetch_all()` | `client.iterate()` |
| Timeouts | `timeout=30.0` | `Timeout(connect=5.0, read=30.0)` |
| Python | 3.8+ | 3.10+ |

## Step one: run on v2.9 with warnings as errors

Pin v2.9 and run your test suite with deprecation warnings promoted to errors:

```
python -W error::DeprecationWarning -m pytest
```

For an application without much test coverage, set `PYTHONWARNINGS=error::DeprecationWarning` in a staging environment and exercise the real paths. The limitation is the same in both cases: a warning only fires on a line that actually executes, so a rarely used branch that builds a `Client` or reads a `dict` key will stay silent through the whole exercise and then fail in production on v3. Grep for the five patterns as well, because they are all mechanically greppable: `Client(`, `fetch_all`, `timeout=`, and subscript access on anything a client method returned.

## Construction

`Client` now takes a single `ClientConfig` instead of a URL and a token:

```python
# v2
client = Client("https://api.example.com", "tok_abc")

# v3
client = Client(ClientConfig.from_url("https://api.example.com", "tok_abc"))
```

For call sites that passed nothing but a URL and a token, `from_url` is a pure textual substitution and you can do them all in one pass. Call sites that passed additional keyword arguments need a decision instead: build a `ClientConfig` directly and set the fields there, which is also where the new timeout object goes.

## Typed return values

Methods that returned `dict` now return dataclasses, so key access becomes attribute access throughout:

```python
# v2
result = client.get_page(1)
for item in result["items"]:
    print(item["id"])

# v3
result = client.get_page(1)
for item in result.items:
    print(item.id)
```

The direct subscripts are the easy half, and they fail loudly. The half worth searching for deliberately is everywhere a result was treated as a mapping without being subscripted: `result.get("items", [])`, `"items" in result`, `**result` in a call, `json.dumps(result)`, or iteration that assumed keys. Serialisation boundaries are the most common survivor here, and `dataclasses.asdict(result)` is the replacement at the point where you genuinely need a dict to hand to something else.

## `fetch_all()` is removed

`iterate()` yields pages rather than accumulating them, which is the point of the change:

```python
# v2
for item in client.fetch_all():
    process(item)

# v3
for page in client.iterate():
    for item in page.items:
        process(item)
```

If some caller truly needs the whole set in memory, `[item for page in client.iterate() for item in page.items]` reproduces the old behaviour and the old memory profile. Prefer restructuring the caller to stream. Code that took a length, indexed into the result, or made two passes over it is where this migration takes real work rather than mechanical editing, so find those call sites before you start.

## Timeouts

Passing a float now raises `TypeError` rather than warning, so every `timeout=` argument has to be converted:

```python
# v2
timeout=30.0

# v3
timeout=Timeout(connect=5.0, read=30.0)
```

Resist the obvious substitution of `Timeout(connect=30.0, read=30.0)`. The old float was a single budget, and splitting it across both phases doubles your worst case from 30 seconds to 60. A connect timeout wants to be short, a few seconds at most, because a connection that has not been established quickly is usually not going to be; keep your old value on `read`, which is the phase it was really governing.

## Python 3.10

The interpreter bump is the one change you cannot make from v2.9, since 3.8 reached end of life in October 2024 and gets no security fixes. Do it as its own commit, before the version bump rather than alongside it, so that if something breaks you know whether it was the library or the runtime.

## After the upgrade

Three additions are available once you are on v3, none of which require changes to working code. `AsyncClient` mirrors the sync API for codebases already running an event loop. Retry on 429 is automatic and honours `Retry-After`, so hand-rolled backoff around rate limits can come out, and leaving it in means two layers of retry multiplying each other's delays. Structured logging hooks replace whatever you were doing to get request detail out of the client.