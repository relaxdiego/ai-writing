# Migrating from v2 to v3

v3 changes five things that will break existing code, and adds three that won't. The maintainers do not ship a codemod, so the upgrade is a manual pass over your call sites. It is much less painful if you go through 2.9 rather than jumping straight to 3.0, for reasons described below.

## Raise your Python floor first

v3 requires Python 3.10. If you are still on 3.8, do that upgrade on its own, on v2, and get it green before touching the library. Mixing a runtime bump with an API bump means every failure has two candidate causes.

## Go through 2.9

2.9 is a v2 release that emits a `DeprecationWarning` for each of the changes below and accepts both the old and the new form. The intended sequence is: pin to 2.9, turn warnings into failures, fix everything they point at, then bump to 3.0 and expect no further changes.

```
pip install 'yourlib>=2.9,<3'
python -W error::DeprecationWarning -m pytest
```

One caveat worth taking seriously: a runtime warning only fires on a line that actually runs. Your test suite is the coverage boundary for this technique, and the parts of your code it doesn't exercise will fail in production instead. After the warnings are clean, grep for the old spellings as well:

```
grep -rn 'fetch_all\|timeout=' --include='*.py' .
grep -rnE 'Client\([^)]*,' --include='*.py' .
```

The dict-to-dataclass change is the one that hides best from both techniques, since key access can be spelled in ways grep won't catch. Budget a real read of the code that consumes results.

## Client construction

The two positional arguments are gone, replaced by a single config object.

```python
# v2
client = Client("https://api.example.com", "tok_123")

# v3
client = Client(ClientConfig.from_url("https://api.example.com", "tok_123"))
```

`from_url` covers the case where you only have a URL and a token, and it is the right call for most upgrades: it keeps the change to a single line per call site. Construct `ClientConfig` directly only when you need to set something the helper does not expose, such as the new timeout or retry settings.

If you build clients in more than a few places, this is a good moment to move construction into one factory function so the next signature change costs you one edit.

## Results are dataclasses, not dicts

Every method that returned a `dict` now returns a typed dataclass, and key access becomes attribute access.

```python
# v2
result["items"]
result["page"]["next"]

# v3
result.items
result.page.next
```

Straight lookups are mechanical. The cases that need thought are the ones that treat the result as a mapping rather than as a record:

- `result.get("items", [])` has no direct equivalent. The field always exists on the dataclass, so the default was either dead code or a sign you were handling two different response shapes. Decide which.
- `json.dumps(result)` will now raise. Use `dataclasses.asdict(result)` first.
- `**result` and `dict(result)` no longer work; unpack the fields you want explicitly.
- Iterating the result, or `"items" in result`, was iterating keys. Those checks are almost always redundant now and should be deleted rather than translated.

The upside is that your type checker can see these accesses. If you run mypy or pyright, a full run after this change will find the call sites your tests missed, which is the most reliable coverage you will get for this particular migration.

## `fetch_all()` is gone; use `iterate()`

`fetch_all()` accumulated the entire result set in memory before returning. `iterate()` yields pages instead, so memory stays flat regardless of how large the result is.

```python
# v2
for item in client.fetch_all():
    handle(item)

# v3
for page in client.iterate():
    for item in page.items:
        handle(item)
```

Note the extra level: `iterate()` yields pages, not items. If you want the flat stream, flatten it yourself and keep it lazy:

```python
from itertools import chain
items = chain.from_iterable(page.items for page in client.iterate())
```

You can reproduce the old behaviour with `list(...)` around that expression, and sometimes that is genuinely what you want, for instance when the caller needs a length or has to sort the whole set. But writing it out puts the memory cost where a reader can see it, which was the point of removing the method.

Anything that relied on the return value being a list, such as `len()`, indexing, or a second pass over the same data, needs a decision rather than a translation: either materialise deliberately or restructure into a single streaming pass.

## Timeouts are objects, and floats now raise

```python
# v2
client.get(url, timeout=30.0)

# v3
client.get(url, timeout=Timeout(connect=5.0, read=30.0))
```

The float form raises `TypeError` in v3 rather than warning, so any call site you miss fails loudly at runtime instead of quietly doing the wrong thing. Since the old single value covered the whole operation, mapping it to `read` and choosing a shorter `connect` preserves roughly the old behaviour; a connect timeout of a few seconds is usually right, because a connection that hasn't been established quickly generally isn't going to be.

Watch for timeouts that arrive from configuration files or environment variables, where the value is parsed as a float somewhere far from the call. Those are the ones the grep above will not find.

## What you get in return

Three additions need no changes to adopt.

`AsyncClient` mirrors the sync API with `async`/`await`, including `iterate()` as an async generator. It is a separate class, so you can adopt it one code path at a time.

Retries on HTTP 429 are now automatic and honour the `Retry-After` header. If you built your own 429 backoff on v2, delete it, or you will be sleeping twice per rate-limited request.

Structured logging hooks let you attach to request and response events without monkeypatching. Configure them through `ClientConfig`, which is a second reason to have a single place where clients are built.

## Verifying the result

After the bump to 3.0, the checks worth running are a type-checker pass over the whole codebase, not just the diff; a search confirming no `fetch_all` or bare-float `timeout=` survives; and an integration test that exercises a paginated endpoint end to end, since pagination is where the dataclass change and the `iterate()` change interact.