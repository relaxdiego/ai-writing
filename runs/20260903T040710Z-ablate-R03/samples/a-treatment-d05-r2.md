# Migrating from v2 to v3

Version 3 changes five things that will break existing code: the client constructor, the return type of every method, the removal of `fetch_all()`, the timeout representation, and the minimum Python version. There is no codemod, so every call site has to be visited by hand. The maintainers recommend doing that in two passes rather than one. Upgrade to v2.9 first, which is API-compatible with v2 but emits a `DeprecationWarning` for each of the changes below, then run your test suite with warnings made visible and fix what it reports:

```
python -W error::DeprecationWarning -m pytest
```

Turning the warnings into errors is the point of the exercise. It converts a migration you would otherwise perform by grepping into one the interpreter drives for you, and it finds the call sites that live in branches your grep patterns miss. Only once v2.9 runs clean should you bump to v3, at which point the same call sites raise real exceptions instead of warnings.

## Python 3.10 is now the minimum

Support for 3.8 is dropped. Check your CI matrix, your Dockerfiles and your `python_requires` before anything else, because if you are still on 3.8 the rest of this guide is blocked on that move. Nothing in the v2.9 step requires 3.10, so you can complete the deprecation pass on your current interpreter and treat the version bump as a separate, independently reviewable change.

## Client construction takes a config object

`Client(url, token)` no longer works. The constructor accepts a single `ClientConfig`, which gives the growing set of connection options somewhere to live that is not a widening positional signature:

```python
# v2
client = Client("https://api.example.com", token)

# v3
client = Client(ClientConfig.from_url("https://api.example.com", token))
```

`ClientConfig.from_url` covers the case where you have nothing but a URL and a token, and for most call sites the migration is that one-line wrap. If you were passing other keyword arguments to the constructor, build the config directly instead and set them there. A useful side effect of the change is that configuration becomes a value you can construct once, store, and pass around, so applications that were threading a URL and a token through several layers can thread one object instead.

## Methods return dataclasses, not dicts

Every method that returned a `dict` now returns a typed dataclass, and key access becomes attribute access:

```python
# v2
result["items"]
result["page"]["next"]

# v3
result.items
result.page.next
```

The mechanical part of this is a search for subscripts on returned values, but three patterns need more than a textual substitution. Calls to `result.get("items", [])` have no direct equivalent, because a dataclass field either exists or the attribute name is wrong; where you were relying on `.get` to tolerate a missing key, the field is now always present and you should read it directly, and where you were tolerating an optional value, check for `None`. Dictionary unpacking such as `f(**result)` no longer works and wants `dataclasses.asdict(result)`. Anything that serialised a result straight to JSON needs the same treatment, since `json.dumps` will not accept a dataclass instance.

The compensation for the churn is that misspelling a field is now an `AttributeError` at the point of the mistake, and your type checker and editor know what the fields are without a stub.

## `fetch_all()` is removed in favour of `iterate()`

`fetch_all()` accumulated the entire result set in memory before returning it, which is why it is gone rather than deprecated indefinitely. `iterate()` yields pages instead, so memory stays flat regardless of how large the result set is:

```python
# v2
for item in client.fetch_all():
    process(item)

# v3
for page in client.iterate():
    for item in page.items:
        process(item)
```

Note the extra level of nesting: `iterate()` yields pages, not items. If you want a flat stream of items, `itertools.chain.from_iterable(page.items for page in client.iterate())` gives you one while preserving the laziness. You can also recover the old behaviour with `list(...)` around that expression, and doing so is reasonable when a caller genuinely needs the whole set at once, for example to sort it. Reach for it deliberately rather than as a reflex, since it reinstates exactly the memory cost the removal was meant to avoid.

## Timeouts are a `Timeout` object

A float is no longer accepted anywhere a timeout is expected, and passing one raises `TypeError` rather than warning. Connect and read timeouts are now specified separately:

```python
# v2
client.get(path, timeout=5.0)

# v3
client.get(path, timeout=Timeout(connect=2.0, read=10.0))
```

Splitting the two values means the single number you used to pass has no faithful translation, so decide what it was protecting against. If it was guarding against an unreachable host, most of it belongs in `connect`; if it was bounding a slow query, it belongs in `read`. A short connect timeout with a longer read timeout is the usual shape, because failing to establish a connection is nearly always fast when it is going to succeed at all, whereas a legitimate response can take a while to arrive.

## What you get in return

Three additions come with v3 and none of them require changes to migrate. `AsyncClient` mirrors the synchronous API and accepts the same `ClientConfig`, so an async port is a matter of awaiting the calls rather than relearning the surface. Retries on HTTP 429 are now automatic and honour the `Retry-After` header, which means any hand-rolled backoff you wrapped around rate-limited calls can probably come out; check that yours is not doing something extra, such as failing over to a different endpoint, before you delete it. Structured logging hooks let you attach a handler that receives request and response metadata as fields rather than as formatted strings, which is worth wiring up during the migration while you are already touching the client setup code.