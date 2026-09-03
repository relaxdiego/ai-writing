# Migrating from v2 to v3

Version 3 changes the client constructor, the return type of every method, the timeout API, and the minimum Python version. None of it is subtle, but there is no codemod, so the work is mechanical and proportional to how much of the API you touch. The path the maintainers recommend is to upgrade to 2.9 first, run your test suite and your application under `-W error::DeprecationWarning`, and fix everything that fires. Every breaking change below is warned about in 2.9, so a clean run there means the jump to 3.0 is mostly a version bump. Going straight from 2.8 to 3.0 works too, but you will find the breakages as `TypeError` and `AttributeError` at runtime rather than as a list of warnings you can work through in one pass.

## Python 3.10 is the floor

Support for 3.8 is dropped and 3.9 is not supported either; 3.10 is the minimum. Do this part before touching library code, because the rest of the migration is easier to validate on the interpreter you will actually ship on. If you are pinned to 3.8 by another dependency, stay on the 2.9 line, which continues to support it and which carries the retry and logging work backported where it was possible to do so without breaking the API.

## Constructing the client

The two-positional-argument constructor is replaced by a single configuration object:

```python
# v2
client = Client("https://api.example.com", token)

# v3
client = Client(ClientConfig.from_url("https://api.example.com", token))
```

`ClientConfig.from_url` exists precisely so that the common case stays one line. Reach for the full constructor when you need to set anything else on the config, since that is where timeouts, retry policy, and logging hooks now live rather than being scattered across per-call keyword arguments. If you build clients in more than a handful of places, it is worth introducing a small factory function of your own during the 2.9 step, so that the eventual change lands in one file instead of forty.

## Results are dataclasses, not dicts

Every method that returned a `dict` now returns a typed dataclass, and key access becomes attribute access:

```python
# v2
for item in result["items"]:
    print(item["id"])

# v3
for item in result.items:
    print(item.id)
```

This is the change most likely to reach into your own code rather than staying at the boundary, because dicts leak: anything you passed a result into, serialised, or merged into another dict now needs adjusting. The compensation is that a typo in a field name is a static error and an editor can complete the field list. Where you genuinely need a dict at the edge of your system, `dataclasses.asdict` on the result gives you one, and the field names match the old keys, so existing serialisation code will usually keep working unchanged.

## `fetch_all()` is removed

`fetch_all()` accumulated the entire result set in memory before returning, which is the reason it is gone rather than deprecated in place. Use `iterate()`, which yields pages:

```python
# v2
items = client.fetch_all(query)

# v3
items = [item for page in client.iterate(query) for item in page.items]
```

That rewrite reproduces the old behaviour and the old memory profile, and it is a reasonable first move if you want the upgrade to be behaviour-preserving. The point of the change is to make the cost visible so you can decide whether to pay it, and in most call sites you can push the per-item work inside the loop and never hold more than one page at a time.

## Timeouts

A float is no longer accepted and no longer means anything on its own, since the connect and read budgets are now separate:

```python
# v2
client = Client(url, token, timeout=30.0)

# v3
config = ClientConfig.from_url(url, token)
config.timeout = Timeout(connect=5.0, read=30.0)
```

Passing a float raises `TypeError` rather than warning, so this one cannot slip through into production silently. When you are splitting an old single value, a short connect timeout with the old value kept as the read timeout usually preserves the behaviour you were relying on, because a connect that has not completed in a few seconds is not going to complete.

## What arrives with the upgrade

Three additions come with v3 and none of them require changes. `AsyncClient` mirrors the synchronous API with the same config object and the same dataclass returns, so an async port is a matter of awaiting calls rather than relearning the surface. Retries on 429 now happen automatically and honour `Retry-After`, which means any hand-rolled backoff you wrapped around the v2 client is likely redundant and worth deleting during the migration rather than after, since two competing retry layers turn one rate-limit response into a long, confusing stall. Structured logging hooks are configured on `ClientConfig` and emit request and response records you can route into whatever you already use, replacing whatever you were inferring from the standard library logger's free-text output.