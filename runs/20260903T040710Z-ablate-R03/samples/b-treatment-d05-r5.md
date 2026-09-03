# Migrating from v2 to v3

There is no codemod for this release, and the changes touch construction, return types, iteration, and timeouts, so a direct jump from v2.8 to v3 tends to surface errors one traceback at a time. Upgrade in two steps instead. Pin to v2.9 first, which is functionally identical to v2.8 but emits a `DeprecationWarning` for every construct that v3 removes; run your test suite with `-W error::DeprecationWarning` so those warnings fail loudly rather than scrolling past; fix them all under v2.9, where both the old and new spellings work; then move the pin to v3, which should be a no-op if the warnings are clear. Note that v2.9 still supports Python 3.8, so you can do the whole warning-fixing pass on your current interpreter and treat the interpreter upgrade as a separate change.

## Python version

v3 requires Python 3.10 or newer. If you are on 3.8, plan that upgrade before the library upgrade rather than alongside it, since the failure modes look nothing alike and debugging them together is miserable. 3.9 users have no deprecation warning to guide them here: the version floor is enforced by the package metadata, so a `pip install` on 3.9 will simply refuse to resolve v3.

## Constructing a client

`Client(url, token)` is gone in favour of a single configuration object, which is what makes room for the retry and logging settings described below without another decade of positional arguments.

```python
# v2
client = Client("https://api.example.com", "sk-...")

# v3
client = Client(ClientConfig.from_url("https://api.example.com", "sk-..."))
```

`ClientConfig.from_url` covers the case where you have nothing but a URL and a token, and it is the mechanical translation for most call sites. Construct `ClientConfig` directly when you need to set anything else, since `from_url` takes no other parameters by design.

## Return types

Every method that returned a `dict` now returns a dataclass, so key access becomes attribute access: `result["items"]` becomes `result.items`. This is the change that touches the most lines and the one v2.9 helps with least, because the deprecation shim can only warn when a returned mapping is subscripted, and code that passes results into `json.dumps`, into a template, or into anything that iterates keys will not trigger it. Search for subscripting on call results directly rather than trusting the warnings to be exhaustive.

Two consequences are worth knowing before you start. Unknown keys no longer survive a round trip: a field the server sends that the dataclass does not declare is dropped, so if you were relying on passthrough of undocumented fields, check the release notes for whether that field is now declared. And `.get()` with a default has no equivalent; use `getattr(result, "name", default)` only for genuinely optional attributes, and prefer checking for `None` on fields that are declared but nullable.

## Pagination

`fetch_all()` is removed with no replacement of the same shape. It accumulated the entire result set in memory, which is fine for a few hundred records and a problem at a few hundred thousand. `iterate()` yields pages, so the translation depends on what you did with the list:

```python
# v2
for item in client.fetch_all():
    process(item)

# v3
for page in client.iterate():
    for item in page.items:
        process(item)
```

If you truly need the whole set materialised, `[item for page in client.iterate() for item in page.items]` reproduces the old behaviour, including its memory profile. Reach for that only when something downstream needs random access or a length, and be aware that you are reintroducing the reason the method was removed.

## Timeouts

Timeouts are no longer a float. They are a `Timeout` object carrying separate connect and read values, so that a slow-to-establish connection and a slow response can be distinguished. Passing a float raises `TypeError` in v3 rather than warning, which means any timeout you set from configuration, an environment variable, or a caller's keyword argument will fail at runtime rather than at import.

```python
# v2
client.request(path, timeout=5.0)

# v3
client.request(path, timeout=Timeout(connect=5.0, read=5.0))
```

Splitting the old single value across both fields preserves v2 behaviour closely enough for most callers. If you were setting a generous timeout mainly to tolerate slow responses, this is a good moment to tighten `connect` and leave `read` long, which is the distinction the change exists to enable.

## What you get in return

None of these require action, but they may let you delete code. `AsyncClient` mirrors the synchronous API and takes the same `ClientConfig`, so an async migration no longer means a separate HTTP layer. Retries on `429` are automatic and honour the `Retry-After` header, so hand-rolled backoff around rate limits can usually come out; check first that your wrapper is not also retrying on statuses the library leaves alone. And structured logging hooks replace whatever you were doing with request-level instrumentation, emitting events with stable field names rather than formatted strings.