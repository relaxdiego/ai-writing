# Migrating from v2 to v3

## Before you start

v3 requires Python 3.10 or newer. If you're on 3.8, that upgrade comes first — nothing else here matters until the interpreter is sorted.

There is no codemod. The recommended path is to upgrade to **v2.9** first, which emits `DeprecationWarning` for every change listed below while still accepting the old forms. Run your test suite with `-W error::DeprecationWarning` to turn those warnings into failures, fix them all, and then bump to v3. Code that's warning-clean on 2.9 will run unchanged on 3.

## Client construction

`Client` takes a single `ClientConfig` instead of positional URL and token.

```python
# v2
client = Client("https://api.example.com", token)

# v3
client = Client(ClientConfig.from_url("https://api.example.com", token))
```

`from_url` covers the simple case. If you were relying on other constructor arguments, build `ClientConfig` directly.

## Return types

Methods that returned `dict` now return dataclasses. Key access becomes attribute access:

```python
result["items"]   # v2
result.items      # v3
```

This is the change most likely to surface at runtime rather than at import time, since a missing key raises where an unknown attribute would too — but only on the line that touches it. Grep for subscript access on returned values; the deprecation warnings in 2.9 will catch the rest.

Code that did `json.dumps(result)` or `**result` needs adjusting — use `dataclasses.asdict()`.

## `fetch_all()` is removed

`fetch_all()` materialised the entire result set. `iterate()` yields pages instead:

```python
# v2
for item in client.fetch_all():
    process(item)

# v3
for page in client.iterate():
    for item in page.items:
        process(item)
```

If you genuinely need everything in memory, `list(chain.from_iterable(p.items for p in client.iterate()))` reproduces the old behaviour — but consider whether you do.

## Timeouts

Floats are no longer accepted and now raise `TypeError` rather than warning:

```python
# v2
client.request(..., timeout=30.0)

# v3
client.request(..., timeout=Timeout(connect=5.0, read=30.0))
```

The old float applied to the whole operation, so the closest equivalent is to set `read` to your old value and pick a shorter `connect`. Note that 2.9 warns here; v3 raises. This one fails loudly, which makes it the easiest to find and the most disruptive if you skip the 2.9 step.

## What's new

None of these require changes, but they may let you delete code:

- **`AsyncClient`** — same API surface, async methods.
- **Automatic retry on 429**, honouring `Retry-After`. If you wrote your own rate-limit backoff around v2 calls, it's now redundant and may compound with the built-in retry.
- **Structured logging hooks** for request/response instrumentation.