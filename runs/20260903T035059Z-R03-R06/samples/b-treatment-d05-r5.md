# Upgrading from v2 to v3

v3 changes the shape of nearly every entry point: the constructor, the return types, the pagination API, and the timeout argument. None of it is mechanical enough for a codemod, so the recommended path is to land the changes under v2.9 first, where every one of them is a deprecation warning rather than a failure, and only then bump to v3. That way each break surfaces as a warning attached to a line number in your own code instead of as a stack trace from inside the library.

## Upgrade in two steps

Pin `v2.9`, run your test suite with warnings promoted to errors, and work through the results:

```
python -W error::DeprecationWarning -m pytest
```

Or, if your suite is large enough that fixing everything at once is impractical, run it normally and collect the warning summary, then narrow the filter to one category at a time. The important part is that v2.9 warns about all five breaking changes below, so a run that is silent under `-W error::DeprecationWarning` will import and construct cleanly under v3. Once that run is green, bump to `v3` and re-run; what remains should be behavioural differences in pagination rather than API errors.

## Constructor takes a config object

`Client(url, token)` is replaced by `Client(config)`. For the common case, build the config with the helper:

```python
# v2
client = Client("https://api.example.com", token)

# v3
client = Client(ClientConfig.from_url("https://api.example.com", token))
```

`ClientConfig` is where the new options live (timeouts, retry behaviour, logging hooks), so if you construct clients in more than one place it is worth building the config once and passing it around rather than calling `from_url` repeatedly at each call site.

## Return values are dataclasses, not dicts

Every method that returned a `dict` now returns a typed dataclass, and key access becomes attribute access:

```python
# v2
for item in result["items"]:
    print(item["name"])

# v3
for item in result.items:
    print(item.name)
```

The mapping protocol is gone entirely, which catches two idioms that a search for `["` will miss. Code using `result.get("field")` to tolerate absent keys should use the attribute directly, since the dataclass always defines it and gives an explicit `None` where the server sent nothing. Code that passed a response straight into `json.dumps` or a serialisation layer needs `dataclasses.asdict(result)` in between. Field names follow the wire names except where a wire name collided with a Python keyword; those are suffixed with an underscore, and your type checker will point at them.

## `fetch_all()` is removed

`fetch_all()` accumulated the whole result set in memory before returning. `iterate()` replaces it and yields pages, not individual records, so the direct translation adds a level of nesting:

```python
# v2
for item in client.fetch_all():
    process(item)

# v3
for page in client.iterate():
    for item in page.items:
        process(item)
```

If you want a flat stream, `itertools.chain.from_iterable(page.items for page in client.iterate())` gives you one. What you should not do is rebuild the old behaviour with `list(...)` around that expression, since the memory characteristics that motivated the removal come back with it. Note also that requests now happen as you consume the iterator rather than all inside one call, so network exceptions surface partway through your loop; anything that assumed a successful `fetch_all()` meant a complete result set needs to decide what a partially processed set means for it.

## Timeouts are a `Timeout` object

Floats are no longer accepted, and passing one raises `TypeError` rather than warning:

```python
# v2
client.get(path, timeout=5.0)

# v3
client.get(path, timeout=Timeout(connect=2.0, read=5.0))
```

The split between connect and read means there is no single number that preserves old behaviour exactly; the old float applied to the whole operation. Setting `read` to the old value and `connect` to something short is usually right, because a connect phase that takes more than a second or two is failing rather than being slow. Since this raises rather than warns, grep for `timeout=` across the codebase instead of relying on tests to find every site: a timeout argument in an error-handling branch or a rarely-exercised admin path can sit unexercised for a long time and then fail in production.

## Python 3.10 minimum

Support for 3.8 is dropped and 3.9 is not supported either. If you are on 3.8, move the interpreter first and get that green before touching the library version, so that failures from the runtime change and failures from the API change do not arrive interleaved.

## What v3 adds

Once you are on v3, `AsyncClient` mirrors the sync API with the same config object and the same dataclass return types, so an `async def` port of existing code is largely a matter of adding `await` and `async for`. Retries on HTTP 429 are automatic and honour the `Retry-After` header, which means any backoff loop you wrote around rate limiting can be deleted; if yours retried on other status codes too, keep that part and drop only the 429 branch. Structured logging hooks are configured on `ClientConfig` and emit request and response events with the timing and retry counts attached, which is the intended replacement for wrapping calls in your own timing decorators.