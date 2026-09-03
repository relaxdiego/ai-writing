# Migrating from v2 to v3

## Upgrade in two steps

There is no codemod for this release. The path that works is to land on v2.9 first — it emits deprecation warnings for every change below while still behaving like v2 — clear the warnings, then jump to v3.

```
pip install 'yourlib>=2.9,<3'
python -W error::DeprecationWarning -m pytest
```

Turning warnings into errors converts the migration into a finite checklist: each failure points at one call site that needs changing. Work through them, keep the suite green on v2.9, then `pip install 'yourlib>=3'`. The second step should be uneventful — if it isn't, the difference is almost always something the warnings couldn't see, such as a `dict` return value crossing a module boundary.

(Replace `yourlib` with your package name throughout.)

## Python 3.10 is the minimum

v3 drops 3.8. Do this before anything else, because it constrains everything else: if you're pinned to 3.8 by another dependency, the rest of the migration is blocked and worth knowing about now rather than three files in.

## `Client(url, token)` → `Client(config)`

The constructor now takes a single `ClientConfig`. For the common case, use the helper:

```python
# v2
client = Client("https://api.example.com", token)

# v3
client = Client(ClientConfig.from_url("https://api.example.com", token))
```

If you construct clients in more than two or three places, wrap it once in your own factory rather than editing each site — you'll want a single place to set timeouts and retries later anyway.

## Return values are dataclasses, not dicts

Every method that returned a `dict` now returns a typed dataclass. Key access becomes attribute access:

```python
# v2
result["items"]
result["page"]["next"]

# v3
result.items
result.page.next
```

The mechanical replacements are easy. The ones that bite are the places where a result was treated as a generic mapping:

- `result.get("items", [])` has no direct equivalent. The field always exists; it's `None` or empty rather than missing, so `result.items or []` is usually what you meant.
- `json.dumps(result)` and `**result` both fail. Use `dataclasses.asdict(result)`.
- `for key in result:` and `"items" in result` fail. If you were probing shape at runtime, the type now tells you the shape statically — that check can generally go.
- Anything that stored a result in a cache, queue, or database as JSON needs `asdict()` at the boundary.

That last category is the one v2.9's warnings will not catch, because passing a dataclass to your own serializer is not a deprecated call. Grep for the serialization points rather than trusting the warnings alone.

## `fetch_all()` is gone; use `iterate()`

`fetch_all()` pulled the whole result set into memory. `iterate()` yields pages instead:

```python
# v2
for item in client.fetch_all()["items"]:
    process(item)

# v3
for page in client.iterate():
    for item in page.items:
        process(item)
```

You *can* restore the old behaviour with `[i for page in client.iterate() for i in page.items]`, and for a query you know returns forty rows that's a reasonable thing to do. For anything unbounded it reintroduces exactly the problem the removal was meant to fix. Where the old code did `len(...)` or sorted the full list, check whether the API can do it server-side before rebuilding the list client-side.

## Timeouts are objects, not floats

```python
# v2
client.get(url, timeout=30.0)

# v3
client.get(url, timeout=Timeout(connect=5.0, read=30.0))
```

Passing a float raises `TypeError` in v3 — no coercion, no warning. On v2.9 it warns, so the warnings-as-errors run will find these for you.

There's no mechanical translation, because one number can't split into two. The old float was effectively a read timeout, so `Timeout(connect=5.0, read=<old value>)` preserves behaviour closely enough for most callers. Connecting is either fast or broken, and a short connect timeout surfaces a dead host in seconds instead of waiting out a long read budget.

## What you get in v3

None of these require changes, but two of them may let you delete code.

**Automatic retry on 429.** v3 honours `Retry-After` on rate-limited responses. If you have hand-rolled backoff around 429s, it now competes with the built-in behaviour — remove yours or configure the built-in off, but don't run both.

**`AsyncClient`.** Same surface as `Client`, with `async for` on `iterate()`. It's a separate class, so adopting it is a per-call-site decision, not a migration.

**Structured logging hooks.** Useful for replacing whatever you were doing with response inspection to get request timing.

## If you need to roll back

v3 and v2 can't share a call site, so a partial rollback means reverting the whole change set. Keep the v2.9 state on its own commit — it runs on both v2 and, apart from the timeout objects, reads almost identically to v3, which makes it a safe place to sit if you need to pause the upgrade.