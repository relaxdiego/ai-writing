# Migrating from v2 to v3

v3 is a breaking release. The changes are mechanical but numerous, and there is no codemod — every call site has to be touched by hand or by search-and-replace.

The maintainers recommend a two-step upgrade, and you should follow it:

1. Upgrade to **v2.9** first. Every v3 breaking change emits a deprecation warning there.
2. Run your test suite with warnings visible (`python -W error::DeprecationWarning -m pytest`) and fix everything it flags.
3. Then upgrade to v3. If step 2 was clean, step 3 should be close to a no-op.

Doing it in one jump means you find your breakage as `TypeError`s and `AttributeError`s at runtime instead of as a warning list you can work through.

## Before you start: Python 3.10

v3 drops Python 3.8. The minimum is 3.10. If you're on 3.8, resolve that first — you can do it while still on v2, which decouples the interpreter upgrade from the library upgrade. Trying to do both at once makes failures hard to attribute.

## 1. Client construction

`Client(url, token)` is replaced by `Client(config: ClientConfig)`.

```python
# v2
client = Client("https://api.example.com", "tok_abc")

# v3, simple case
client = Client(ClientConfig.from_url("https://api.example.com", "tok_abc"))

# v3, when you need to set anything else
client = Client(ClientConfig(
    url="https://api.example.com",
    token="tok_abc",
    timeout=Timeout(connect=5.0, read=30.0),
))
```

If you construct clients in more than a couple of places, wrap it once in your own factory function now — that gives you a single place to absorb the next configuration change.

## 2. Dicts become dataclasses

Every method that returned `dict` now returns a typed dataclass. Key access becomes attribute access.

```python
# v2
result["items"]
result["page"]["next"]

# v3
result.items
result.page.next
```

This is the change most likely to be missed, because it fails at runtime rather than at import. Some specifics worth planning for:

- **`.get()` with defaults is gone.** `result.get("items", [])` has no direct equivalent. If the field is genuinely optional, it's now typed `| None` and you check it explicitly.
- **Code that iterates keys or does `**result` breaks.** Use `dataclasses.asdict(result)` if you need a dict at a boundary — serialising to JSON, passing to a template, logging.
- **Type checkers now earn their keep.** If you run mypy or pyright, they will find most of these statically. If you don't, this is a good reason to start: without it, your only detection mechanism is test coverage.

A search for `["` on result variables will find most sites, but it's not reliable. The v2.9 warnings are the better instrument.

## 3. `fetch_all()` is removed

`fetch_all()` loaded the entire result set into memory. Use `iterate()`, which yields pages.

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

Note the shape change: `iterate()` yields **pages**, not items. If you want a flat item stream, do it explicitly:

```python
from itertools import chain
items = chain.from_iterable(page.items for page in client.iterate())
```

If some code genuinely needs the whole set materialised — sorting across all results, computing an aggregate that isn't streamable — you can still write `list(chain.from_iterable(...))`. That's a legitimate use, but make it a deliberate choice per call site rather than a reflex. The removal exists because the default should be streaming.

## 4. Timeouts

Floats are no longer accepted. Passing one raises `TypeError` — it does not warn, and does not coerce.

```python
# v2
client.request(..., timeout=30.0)

# v3
client.request(..., timeout=Timeout(connect=5.0, read=30.0))
```

There is no automatic translation from your old float, because the old single value covered both phases ambiguously. You have to decide what the two values should be. A reasonable starting point is a short connect timeout (a few seconds — connecting is either fast or broken) and a read timeout at roughly your old value.

Grep for `timeout=` across your codebase; this one is easy to miss in code paths that aren't exercised by tests, and it fails hard when it is hit.

## 5. What you get in return

None of these require changes, but they may let you delete code:

- **`AsyncClient`** — same API surface, `async`/`await`. If you were running the sync client in a thread pool to get concurrency, you can drop that layer.
- **Automatic retry on 429**, honouring `Retry-After`. If you have hand-rolled rate-limit backoff wrapping this library, check whether it's now redundant — two retry layers stacked on each other produce surprisingly long stalls.
- **Structured logging hooks** — replaces whatever you were doing with request-level instrumentation.

## Suggested order of work

1. Get to Python 3.10 on v2.
2. Upgrade to v2.9. Turn deprecation warnings into errors in CI.
3. Fix construction sites (§1) — smallest, most contained change.
4. Fix timeouts (§4) — grep-able, and the failure mode in v3 is a hard error.
5. Fix `fetch_all()` call sites (§3) — requires thought per site, so do it before the mechanical work while attention is fresh.
6. Fix dict access (§2) — the long tail. Lean on a type checker.
7. Upgrade to v3. Remove any now-redundant retry logic.

## The part that's hardest to verify

Steps 1, 3, 4, and 5 all fail loudly. Step 2 — the dict-to-dataclass change — is the one that can slip through into production, in error handlers, rarely-taken branches, and logging code that a test suite doesn't reach. If you have limited time for this migration, spend it there: run a type checker over the whole codebase after upgrading, and treat untyped or `Any`-typed result variables as unverified rather than clean.