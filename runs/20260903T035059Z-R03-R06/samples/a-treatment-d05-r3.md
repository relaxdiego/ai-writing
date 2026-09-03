# Migrating from v2 to v3

Version 3 changes how a client is constructed, what its methods return, how timeouts are expressed, and which Python versions are supported, and it removes `fetch_all()`. There is no codemod, so every affected call site has to be visited by hand. What the maintainers recommend is that you do that visiting under v2.9 rather than under v3: 2.9 is the last v2 release, it accepts both the old and the new spellings, and it emits a `DeprecationWarning` for each of the old ones. Running your test suite under `python -W error::DeprecationWarning` on 2.9 turns the migration into a list the interpreter hands you, and each item can be fixed and merged separately while the library still works. Once the suite is warning-clean, the move to v3 is a version bump plus whatever your tests do not cover.

## Python 3.10

Version 3 requires Python 3.10 or later; 3.8 is no longer supported. Version 2.9 still runs on 3.8, so you can decouple the two migrations: fix the deprecation warnings first on your current interpreter, then raise the floor to 3.10, then upgrade the library. Doing it in the other order means debugging library changes and interpreter changes in the same commit.

## The constructor takes a config object

`Client(url, token)` becomes `Client(config)`, where `config` is a `ClientConfig`. For the two-argument case there is a helper that produces the same thing:

```python
# v2
client = Client("https://api.example.com", token)

# v3
client = Client(ClientConfig.from_url("https://api.example.com", token))
```

If you construct clients in more than a couple of places, this is the change worth wrapping in a factory function of your own before you start, so that later configuration options land in one place instead of being threaded through every call site.

## Methods return dataclasses, not dicts

Every method that returned a `dict` now returns a typed dataclass, and attribute access replaces key access:

```python
# v2
for item in result["items"]:
    print(item["name"])

# v3
for item in result.items:
    print(item.name)
```

Subscripting a dataclass raises `TypeError`, so the direct `result["items"]` cases surface the first time the line runs. The ones that will cost you time are the places where a result was treated as a mapping rather than indexed: `result.get("items", [])`, `"items" in result`, `**result` splats into another function, and `json.dumps(result)` at a serialization boundary. None of these has a mechanical replacement, because each one was relying on a different property of dicts. For serialization specifically, `dataclasses.asdict(result)` will reproduce the old payload, and it is worth using at the edges of your system so that response shapes you have published to other services do not change underneath them. Inside your own code, prefer reading the attributes; the types are the point of the change.

## `fetch_all()` is gone

`Client.fetch_all()` built the entire result set in memory before returning it. Its replacement, `Client.iterate()`, yields pages, so consumers gain a level of nesting:

```python
# v2
for item in client.fetch_all():
    process(item)

# v3
for page in client.iterate():
    for item in page.items:
        process(item)
```

Where the flat sequence matters, `itertools.chain.from_iterable(page.items for page in client.iterate())` restores it without materializing anything. Where you genuinely need the whole list at once, a comprehension over both loops gives you back v2's memory profile, and writing it out explicitly at least makes that cost visible in the code.

## Timeouts are objects

A timeout is now a `Timeout` with separate connect and read values, and passing a float raises `TypeError` instead of warning:

```python
# v2
timeout=5.0

# v3
timeout=Timeout(connect=5.0, read=5.0)
```

Passing the old value for both fields preserves the previous behaviour most closely, but it is rarely what you want once you are editing the line anyway: connect timeouts are usefully short, since a connection that has not been established in a second or two is unlikely to be established at all, while read timeouts need to cover the slowest response you are willing to wait for. Watch for timeouts that arrive from configuration rather than from source: values read out of environment variables, settings files, or feature flags are floats at the point of use, will not be caught by grep, and can raise `TypeError` on a production path your tests never touch. Converting at the boundary where you parse configuration is the safest treatment.

## What v3 adds

Nothing here requires action, but the additions may change how you write the code you are already touching. `AsyncClient` mirrors the synchronous API with `async`/`await`, including `iterate()` as an async generator. Retries on HTTP 429 are now automatic and honour the `Retry-After` header, so hand-rolled backoff around rate-limited calls can usually be deleted; if you keep it, the two layers will compound their waits. Structured logging hooks let you attach a callback that receives request and response metadata as records rather than formatted strings, which is the intended replacement for wrapping client methods to log around them.