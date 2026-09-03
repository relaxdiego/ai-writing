# Migrating from v2 to v3

v3 is a breaking release. The changes are mostly mechanical, but there are a lot of call sites in a typical codebase, and there is no codemod. Budget accordingly.

## Recommended path: go through v2.9 first

Don't jump straight to v3. v2.9 is a v2-compatible release that emits `DeprecationWarning` for every construct that v3 removes or changes. The workflow:

1. Upgrade to v2.9. Nothing breaks.
2. Turn warnings into errors in your test suite and fix everything that surfaces.
3. Upgrade to v3. If step 2 was thorough, this is a no-op.

To make the warnings visible (they're suppressed by default in most setups):

```bash
python -W error::DeprecationWarning -m pytest
```

Or in `pytest.ini` / `pyproject.toml`:

```ini
[pytest]
filterwarnings =
    error::DeprecationWarning
```

Warnings only fire on code paths that actually execute, so coverage of your call sites matters here. Grepping for the patterns below is a useful complement — deprecation warnings will not find the call site in the error branch you never test.

## Prerequisite: Python 3.10

v3 drops Python 3.8 and 3.9. Minimum is 3.10. If you're on 3.8, do the interpreter upgrade as its own separate change, before any of this — mixing a runtime upgrade with a library upgrade makes failures much harder to attribute.

## 1. Client construction

`Client(url, token)` is gone. The constructor takes a single `ClientConfig`.

```python
# v2
client = Client("https://api.example.com", "tok_123")

# v3, simple case
client = Client(ClientConfig.from_url("https://api.example.com", "tok_123"))

# v3, when you need to set anything else
client = Client(ClientConfig(
    url="https://api.example.com",
    token="tok_123",
    timeout=Timeout(connect=5.0, read=30.0),
))
```

If you construct clients in more than a couple of places, wrap it once in your own factory function now — while you're still on v2.9 — and migrate the factory rather than every call site.

## 2. Dicts become dataclasses

Every method that returned `dict` now returns a typed dataclass. Key access becomes attribute access.

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

This is the change most likely to bite you at runtime rather than at import time. Things to check specifically:

- **`.get()` with a default.** `result.get("cursor")` has no direct equivalent; the field is always present on the dataclass, typically as `None`. Use `result.cursor` and check for `None`.
- **Serialization.** `json.dumps(result)` no longer works. Use `dataclasses.asdict(result)` first, or whatever `to_dict()` helper the release notes point at.
- **Anything that treats the response as a mapping** — `**result`, `result.keys()`, iteration, `in` checks. These fail with `TypeError` or `AttributeError` rather than returning wrong data, which is the good outcome.
- **Code that passes responses into generic helpers.** A function that takes "a dict from the API" and does `data["x"]` will break at the innermost frame, far from the call you changed.

The upside: your type checker now catches typos in field names. Running mypy or pyright after this step is worth the effort, because it finds statically what the deprecation warnings can only find dynamically.

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

Note the shape change: `iterate()` yields **pages**, not individual items. If you want a flat stream:

```python
from itertools import chain

for item in chain.from_iterable(page.items for page in client.iterate()):
    process(item)
```

Watch for code that relied on having the full list: `len(items)`, indexing, sorting the whole set, or iterating twice. If you genuinely need everything in memory — a small result set you sort and re-read — do it explicitly so the cost is visible at the call site:

```python
items = [item for page in client.iterate() for item in page.items]
```

That's the same memory profile as the old `fetch_all()`, but now it's your line of code, and the reviewer can see it.

## 4. Timeouts

Floats are no longer accepted. Passing one raises `TypeError` — it does not warn and coerce.

```python
# v2
client = Client(url, token, timeout=30.0)

# v3
client = Client(ClientConfig(
    url=url,
    token=token,
    timeout=Timeout(connect=5.0, read=30.0),
))
```

The old single float was effectively a total budget. There's no automatic translation to the two-value form, so you have to make a decision per call site. A reasonable default: keep your old value as `read`, and set `connect` to something short (5s is typical) since connection establishment failing slowly is rarely useful.

Be aware this changes behaviour, not just syntax: the worst case is now roughly `connect + read` rather than your single old number. If you had a hard end-to-end SLA built on the old timeout, enforce it a level up rather than assuming the client still caps total time.

## What you get in v3

None of these require changes, but they may let you delete code:

- **`AsyncClient`** — same API surface, `async`/`await`. Useful if you'd built thread pools around the sync client.
- **Automatic retry on 429**, honouring `Retry-After`. If you have hand-rolled rate-limit backoff, check whether it's now redundant or, worse, stacking with the built-in retry and multiplying your wait times.
- **Structured logging hooks** — if you were parsing log lines or monkeypatching to get request visibility, there's a supported path now.

## Suggested order

1. Upgrade the interpreter to 3.10+, ship it, confirm it's stable.
2. Upgrade to v2.9, turn on `error::DeprecationWarning` in CI.
3. Fix construction and timeouts first — they're localized and mostly mechanical.
4. Fix `fetch_all()` call sites; these need real thought about memory and iteration shape.
5. Fix dict access last, leaning on a type checker to find what tests miss.
6. Upgrade to v3.

Steps 3–5 are all shippable independently while still on v2.9, which is the main reason the two-step path is worth it: you get small reviewable changes instead of one enormous one that can't be bisected.