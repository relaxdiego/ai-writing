# Migrating from v2 to v3

## Before you start

There is no codemod. Every breaking change in v3 has a deprecation warning in **v2.9**, so the supported path is two steps:

1. Upgrade to v2.9. Run your test suite with warnings visible:
   ```
   python -W error::DeprecationWarning -m pytest
   ```
   (Or `-W default::DeprecationWarning` first if failing on every warning is too disruptive.)
2. Fix every warning. Your code will still be running on v2.9 when you're done.
3. Upgrade to v3. Nothing should break.

Doing it in one jump is possible but you lose the warnings as a checklist, and the timeout change in particular becomes a runtime `TypeError` instead of a nudge.

## Prerequisite: Python 3.10

Python 3.8 support is dropped; the minimum is 3.10. Do this move first and separately — it's independent of the library upgrade, and mixing the two makes failures harder to attribute.

## 1. Client construction

`Client(url, token)` is now `Client(config: ClientConfig)`.

```python
# v2
client = Client("https://api.example.com", "token-abc")

# v3, simple case
client = Client(ClientConfig.from_url("https://api.example.com", "token-abc"))

# v3, when you need to set other options
client = Client(ClientConfig(
    url="https://api.example.com",
    token="token-abc",
    timeout=Timeout(connect=5.0, read=30.0),
))
```

If you construct clients in more than a couple of places, add a small factory in your own code now — it gives you one spot to edit for this and future config changes.

## 2. Return types are dataclasses

Methods that returned `dict` now return typed dataclasses. Key access becomes attribute access:

```python
# v2
result["items"]
result["page"]["next"]

# v3
result.items
result.page.next
```

Things to watch for beyond the obvious `[...]` sites:

- `result.get("items", [])` — there's no `.get()`. Use `result.items` and rely on the type; the field always exists.
- `"items" in result` and `for key in result` — membership and iteration over keys are gone. If you were probing for optional fields, check for `None` instead.
- `json.dumps(result)` — dataclasses aren't JSON-serializable. Use `dataclasses.asdict(result)`.
- `**result` splatting into another call — use explicit attributes or `asdict()`.

The upside: your type checker and editor now know these shapes, so a `mypy` or `pyright` run over your codebase after the v2.9 step will find most of the remaining sites for you.

## 3. `fetch_all()` is removed

`fetch_all()` loaded the whole result set into memory. Use `iterate()`, which yields pages.

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

Note it yields **pages, not items** — the extra loop is easy to miss and produces confusing errors if you forget it.

If you genuinely need the full list in memory (small, bounded result sets):

```python
items = [item for page in client.iterate() for item in page.items]
```

But if you're reaching for that on an unbounded set, the removal is telling you something: the streaming form is why `fetch_all` went away.

Also check for code that relied on `len(items)` or indexing before processing. A generator gives you neither; you'll need to either collect first or restructure.

## 4. Timeouts

Timeouts are now a `Timeout` object with separate connect and read values. **Passing a float raises `TypeError`** — it does not warn and coerce.

```python
# v2
client = Client(url, token, timeout=30.0)

# v3
timeout = Timeout(connect=5.0, read=30.0)
```

Your old single float was effectively a total budget. The closest equivalent is a short connect timeout (a few seconds — connecting either works fast or doesn't work) and your old value as the read timeout. If you had timeouts tuned against real latency data, re-check them; the split changes what each number means.

Because this one fails loudly, grep for `timeout=` before upgrading rather than discovering it in production.

## What you get in return

None of these require changes, but they may let you delete code:

- **`AsyncClient`** — same API surface, async. Useful if you'd hand-rolled thread pools around the sync client.
- **Automatic retry on 429**, honouring `Retry-After`. If you wrote your own rate-limit backoff, check that it isn't now retrying on top of the library's retries — the two compound into much longer waits than you intended.
- **Structured logging hooks** — replaces log scraping or monkey-patching if you were doing either.

## Checklist

- [ ] On Python 3.10+
- [ ] Upgraded to v2.9, warnings visible in test runs
- [ ] All `Client(...)` calls pass a `ClientConfig`
- [ ] Dict access converted: `[...]`, `.get()`, `in`, iteration, `json.dumps`, `**` splats
- [ ] `fetch_all()` replaced with `iterate()`, with the page-level loop
- [ ] All `timeout=` floats replaced with `Timeout(connect=..., read=...)`
- [ ] Type checker clean
- [ ] Zero deprecation warnings on v2.9
- [ ] Upgraded to v3
- [ ] Custom 429 retry logic removed or checked for double-retry