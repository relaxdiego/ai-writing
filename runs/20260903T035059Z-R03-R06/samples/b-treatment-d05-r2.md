# Migrating from v2 to v3

v3 changes the shape of the client's public surface: how you construct it, what its methods return, and how you page through results. None of it is subtle, but there is no codemod, so every call site has to be visited by hand. The path we recommend is to upgrade to v2.9 first, which emits a `DeprecationWarning` for each of the changes below while still accepting the old form, fix your code until the warnings are silent, and only then move to v3. Run your test suite with `-W error::DeprecationWarning` under 2.9 and the compiler will effectively do your triage for you.

Before any of that, check your interpreter. v3 requires Python 3.10 or later, and 3.8 support is gone. If you are still on 3.8, do the interpreter upgrade as its own change with v2 pinned, because debugging a runtime change and an API change together is miserable.

## Constructing the client

`Client(url, token)` is now `Client(config)`, where `config` is a `ClientConfig`. For the common case where you have nothing but a URL and a token, `ClientConfig.from_url(url, token)` builds one:

```python
# v2
client = Client("https://api.example.com", token)

# v3
client = Client(ClientConfig.from_url("https://api.example.com", token))
```

The indirection buys you a place to put the settings that used to be scattered across keyword arguments, including the timeout and the new logging hooks. If you construct clients in more than two or three places, it is usually worth writing a small factory of your own that returns a configured `Client`, so that the next configuration change touches one function.

## Return types

Methods that returned `dict` now return dataclasses, so key access becomes attribute access: `result["items"]` becomes `result.items`. The rename is mechanical, but grepping for `["` will not find everything, since dynamic access (`result[key]`, `result.get("items", [])`, `**result`) also breaks. Under 2.9 the returned objects are dict subclasses that warn on `__getitem__`, which catches the dynamic cases that a text search misses. Two idioms need real rewriting rather than substitution: `.get("x", default)` becomes `getattr(obj, "x", default)` only if the field may genuinely be absent, and in v3 it usually cannot be, so prefer reading the attribute directly and letting a missing one be an error. Code that serialises results should call `dataclasses.asdict()` instead of passing the object to `json.dumps`.

## Paging

`Client.fetch_all()` is removed with no drop-in replacement, because its behaviour was the problem: it accumulated the entire result set in memory before returning. Use `Client.iterate()`, which yields pages:

```python
# v2
for item in client.fetch_all(query):
    handle(item)

# v3
for page in client.iterate(query):
    for item in page.items:
        handle(item)
```

Callers that genuinely need the whole set materialised can write `[item for page in client.iterate(query) for item in page.items]`, though if you find yourself doing that in a hot path, the removal was aimed at you. Note that anything relying on `len()` of the old return value, or on iterating it twice, needs restructuring rather than a mechanical edit.

## Timeouts

A timeout is now a `Timeout` object with separate `connect` and `read` values, and passing a float raises `TypeError` rather than warning as it did in 2.9:

```python
# v2
client.fetch(query, timeout=5.0)

# v3
client.fetch(query, timeout=Timeout(connect=2.0, read=5.0))
```

The old float applied to the whole operation, so the closest equivalent is to set `read` to your old value and pick a shorter `connect`, on the reasoning that a connection that has not been established in a couple of seconds is not going to be. A timeout on the config applies to every request from that client, which is generally where it belongs; per-call timeouts are for the handful of requests you know to be slow.

## What you get in return

Three additions need no migration work. `AsyncClient` mirrors the synchronous API with `await` and `async for`, and takes the same `ClientConfig`. Retries on HTTP 429 are now automatic and honour the `Retry-After` header, which means any backoff loop you wrote around rate limiting can probably be deleted, and should be, since your loop and the built-in one will otherwise compound. Structured logging hooks are configured on `ClientConfig` and emit request and response events as records rather than formatted strings, so you can route them into whatever your service already uses.