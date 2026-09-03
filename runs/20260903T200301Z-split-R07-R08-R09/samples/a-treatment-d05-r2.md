# Migrating from v2 to v3

Upgrade in two steps: go to v2.9 first, clear every deprecation warning it emits, and only then move to v3. There is no codemod, so the warnings are the only mechanical inventory of what you need to change. Going straight to v3 turns each of the five breaking changes below into a runtime failure discovered one at a time, and the timeout change in particular now raises `TypeError` where v2.9 would have warned and carried on.

The intermediate step works because v2.9 accepts both the old and new forms of everything. You can migrate a call site, run your tests, and commit, with the library working throughout. Once `python -W error::DeprecationWarning -m pytest` (or your equivalent) passes clean, the v3 bump should be close to a no-op.

## Before you start: Python 3.10

v3 requires Python 3.10; 3.8 is no longer supported. If you are still on 3.8, do the v2.9 deprecation work first, on your current interpreter, and treat the interpreter bump as part of the v3 step rather than something to bundle into the source changes. That keeps two independent sources of breakage separated, which matters when a test starts failing and you need to know which change caused it.

## Client construction

The positional `url` and `token` arguments are replaced by a single config object:

```python
# v2
client = Client("https://api.example.com", "tok_123")

# v3
client = Client(ClientConfig.from_url("https://api.example.com", "tok_123"))
```

`ClientConfig.from_url` covers the simple case exactly. Construct `ClientConfig` directly only where you need to set fields that had no v2 equivalent.

## Dictionaries become dataclasses

Every method that returned a `dict` now returns a typed dataclass, so key access becomes attribute access:

```python
# v2
result["items"]

# v3
result.items
```

The mechanical `["x"]` → `.x` rewrite is the easy part. The cases that need thought are the other things your code did with those dicts, all of which now fail:

- `result.get("items", [])` has no direct equivalent. Fields are always present, so use `result.items` and check for `None` if the field is optional.
- `"items" in result` and `for key in result` no longer work. If you were iterating keys to build something generic, `dataclasses.fields(result)` is the replacement.
- `json.dumps(result)` and `**result` need `dataclasses.asdict(result)` first.
- Mutation is gone if the dataclasses are frozen. Where you patched a response before passing it on, use `dataclasses.replace`.

Search for these patterns explicitly. v2.9 can warn on key access, but it cannot warn about a `json.dumps` call that will only break after the return type changes.

## `fetch_all()` is removed

`fetch_all()` loaded the whole result set into memory, which is what the removal is meant to prevent. `iterate()` yields pages instead:

```python
# v2
for item in client.fetch_all()["items"]:
    process(item)

# v3
for page in client.iterate():
    for item in page.items:
        process(item)
```

Where you genuinely need the full set in memory, and you know it is small, flatten it yourself and make the cost visible at the call site:

```python
items = [item for page in client.iterate() for item in page.items]
```

Be careful with code that took `len()` of the old result, indexed into it, or iterated it more than once. A generator supports none of those, and a second `for` loop over the same `iterate()` call silently does nothing.

## Timeouts

Floats are no longer accepted, and passing one raises `TypeError`:

```python
# v2
client.get(path, timeout=5.0)

# v3
client.get(path, timeout=Timeout(connect=5.0, read=5.0))
```

Duplicating the old value into both fields preserves your existing behaviour if the float was the total budget you cared about. It is usually worth splitting them properly: a connect timeout wants to be short, a few seconds at most, while a read timeout should reflect how long the slowest endpoint you call legitimately takes. Timeout values threaded through your own config or CLI flags need converting at the boundary, not at each call site.

## What you get in v3

`AsyncClient` provides an async equivalent of the synchronous client, so an async codebase no longer needs to push calls to a thread pool. Retries on HTTP 429 are automatic and honour `Retry-After`. Structured logging hooks let you emit request and response records into your own logging pipeline rather than parsing the library's log lines.

The retry behaviour deserves one caution even though it is not a breaking change. If you already handle 429 yourself, by catching the error and sleeping, you now have two layers of backoff stacked on each other, and calls that used to fail fast under rate limiting will instead block for as long as the server asks. Remove your own retry loop, or configure the library's off, but do not leave both running.

## Verifying the migration

The signal that step one is finished is a clean test run with deprecation warnings promoted to errors. Add the dataclass-related greps described above, since those escape the warning mechanism, then bump to v3 and run the suite again on 3.10. Anything that surfaces at that point is almost certainly a `fetch_all` caller reached only at runtime or a timeout float coming from configuration rather than from source.