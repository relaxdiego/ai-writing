# Migrating from v2 to v3

v3 changes the shape of the client API in five places, all of them mechanical but none of them automatic. There is no codemod. The path the maintainers recommend is to first upgrade to v2.9, which emits a `DeprecationWarning` for every construct listed below, run your test suite with `-W error::DeprecationWarning` to turn those warnings into failures, and fix them one at a time while still on a version that accepts both old and new forms. Once the warnings are gone your code will run unchanged on v3, and the actual version bump becomes a one-line change to your dependency pin rather than a debugging session.

## Python version

The minimum supported version is now 3.10; 3.8 is dropped. This is worth checking before anything else, because if your deployment target is still on 3.8 the rest of the guide is moot until that moves. v2.9 will warn on import under 3.8 and 3.9.

## Constructing a client

`Client(url, token)` is replaced by `Client(config: ClientConfig)`. For the common case where you have nothing but a URL and a token, the `ClientConfig.from_url` helper reproduces the old behaviour exactly:

```python
# v2
client = Client("https://api.example.com", token)

# v3
client = Client(ClientConfig.from_url("https://api.example.com", token))
```

If you construct clients in more than a couple of places, it is usually worth building the `ClientConfig` once at startup and passing it around, since the config object is where the new timeout and retry settings live and threading a URL/token pair through your call sites will only mean revisiting them later.

## Return types

Every method that returned a `dict` now returns a typed dataclass, so key access becomes attribute access: `result["items"]` becomes `result.items`. The practical difficulty is that this change is invisible to a grep for method names — the breakage happens wherever the returned value is *used*, which may be several functions away from the call. Under v2.9 the returned objects support both forms and warn on subscripting, which means running your tests is a far more reliable way to find these sites than reading the code. Anything that passes results to `json.dumps`, unpacks them with `**`, or checks `"key" in result` needs attention too, since those are dict behaviours the dataclasses do not carry over; `dataclasses.asdict` covers the serialisation case.

## Pagination

`Client.fetch_all()` is removed rather than deprecated-and-kept, because its behaviour — loading an entire result set into memory — was the problem, and no drop-in replacement can preserve it. Use `Client.iterate()`, which yields pages:

```python
# v2
items = client.fetch_all()
for item in items:
    process(item)

# v3
for page in client.iterate():
    for item in page:
        process(item)
```

Where the surrounding code genuinely needs the whole list — a sort across all results, say, or a length check — you can still write `list(chain.from_iterable(client.iterate()))` and accept the memory cost knowingly, which is at least an explicit choice at the call site rather than a hidden one inside the library.

## Timeouts

Timeouts were a float in seconds and are now a `Timeout` object carrying separate connect and read values. Passing a float raises `TypeError` in v3 rather than warning, so this is the change most likely to surface as a hard failure at runtime rather than a test failure:

```python
# v2
client.request(path, timeout=30.0)

# v3
client.request(path, timeout=Timeout(connect=5.0, read=30.0))
```

The old single value applied to the whole operation, so mapping it to `read` and picking a shorter `connect` preserves roughly the previous behaviour while failing faster on unreachable hosts. Because the failure mode is a `TypeError` on a code path that may only run in production, it is worth grepping for `timeout=` directly rather than relying on tests to find every site.

## What you get in return

None of the additions require changes on upgrade. `AsyncClient` mirrors the sync API for `async`/`await` codebases. Retries on HTTP 429 are now automatic and honour the `Retry-After` header, so hand-rolled backoff loops around rate-limited calls can be deleted — and should be, since leaving them in place stacks your delay on top of the library's. Structured logging hooks let you attach request metadata to your own log pipeline instead of parsing the library's output.