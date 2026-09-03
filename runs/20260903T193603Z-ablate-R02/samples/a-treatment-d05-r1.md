# Migrating from v2 to v3

Five things break, and none of them can be fixed mechanically. There is no codemod. The maintainers' advice is to do the upgrade in two moves rather than one: go to v2.9 first, which still behaves like v2 but emits a `DeprecationWarning` for every construct v3 removes, clear those warnings, and only then bump to v3. The intermediate step is worth the extra release cycle, because it converts a pile of import-time and call-time failures into a list you can work through while the code still runs.

## Step one: v2.9 with warnings as errors

Install v2.9 and run your test suite with deprecation warnings promoted to failures:

```bash
pip install 'yourlib>=2.9,<3'
python -W error::DeprecationWarning -m pytest
```

Everything below will now fail loudly at the call site instead of silently continuing.

The limitation to keep in mind is that a deprecation warning is a runtime signal. It fires only on lines that actually execute, so the warnings you see are bounded by your test coverage. Paths that run once a quarter, error handlers, and the branch behind the feature flag nobody has turned on yet will stay quiet in v2.9 and then raise in v3. For each change below there is a static check you can run alongside the warnings; use both.

## Python 3.10 is the floor

Do this first, since it gates the rest. v3 drops 3.8, and 3.9 with it. If you are on 3.8, the runtime upgrade is a separate piece of work from the library upgrade and should land as its own change, ideally before you touch v2.9 at all. Trying to debug a dataclass migration and a Python version bump in the same pull request is how a two-day job becomes a two-week one.

## Constructing the client

`Client(url, token)` is gone. The constructor now takes a single `ClientConfig`:

```python
# v2
client = Client("https://api.example.com", token)

# v3
client = Client(ClientConfig.from_url("https://api.example.com", token))
```

`from_url` covers the simple case and is a straight one-line substitution. If you have a factory or fixture that builds clients from environment variables, that is the one place worth converting properly: build a `ClientConfig` once, pass it around, and let the timeout change below land in the same object rather than being threaded through every call site.

## Dictionaries become dataclasses

Every method that returned a `dict` now returns a typed dataclass, and key access becomes attribute access:

```python
# v2
for item in result["items"]:
    print(item["name"])

# v3
for item in result.items:
    print(item.name)
```

This is the change with the longest tail, because dicts support a lot of operations that dataclasses do not. Subscripting is the obvious one. The less obvious ones are `result.get("items", [])`, `"items" in result`, `**result` in a call or a literal, iteration over the object expecting keys, and anything that hands the value straight to `json.dumps`. Each of these fails differently: `.get` raises `AttributeError`, `in` raises `TypeError`, `json.dumps` raises `TypeError` on a type it cannot serialise. Grep for the method names that return responses and read every use, rather than only chasing the subscripts.

For serialisation, `dataclasses.asdict(result)` from the standard library gives you a plain nested dict and is the shortest path for a payload you were previously forwarding verbatim. Prefer naming the fields you actually need where you can; `asdict` will happily carry along any field the library adds in a future release.

One thing to check rather than assume: attribute names cannot always match the wire format. Any response key that was hyphenated, or that collides with a Python keyword, will have been renamed. Read the field list on the dataclasses you use most before you start rewriting by hand.

## `fetch_all()` is removed

`fetch_all()` loaded the entire result set into memory, which is why it is gone rather than deprecated in place. `iterate()` yields pages:

```python
# v2
for item in client.fetch_all():
    process(item)

# v3
for page in client.iterate():
    for item in page.items:
        process(item)
```

If you would rather keep a flat loop, `itertools.chain.from_iterable(page.items for page in client.iterate())` gives you one back without materialising anything.

Resist the urge to write `list(chain.from_iterable(...))` to make the diff smaller. That reproduces exactly the memory profile the removal was meant to eliminate, and it will work fine on your development data set and fall over on the account with two million rows. If a call site genuinely needs the whole set in memory, such as a sort across all results, keep it, but mark it and know why.

## Timeouts

A float is no longer accepted, and in v3 passing one raises `TypeError` rather than warning:

```python
# v2
client.get(path, timeout=30.0)

# v3
client.get(path, timeout=Timeout(connect=30.0, read=30.0))
```

Splitting one number into two forces a decision you did not previously have to make. The safe literal translation is to set both values to your old float, which is never stricter than what you had. Once you are on v3 and stable, tighten `connect` to something small, a couple of seconds is usually plenty, and leave `read` sized for the slowest endpoint you call. That is the configuration people usually wanted from a single timeout and rarely got.

This is the change where v2.9's coverage limitation bites hardest, because the failure mode is a `TypeError` at call time in whatever path you did not exercise. Grep for `timeout=` across the codebase, including tests and config loaders, and confirm every hit is a `Timeout` before you cut over.

## What you get in return

`AsyncClient` mirrors the sync API for asyncio callers. Nothing about it is required; the sync client is not deprecated.

Retries on HTTP 429 are now automatic and honour `Retry-After`. This is additive to the API but not invisible at runtime: a call that previously returned a 429 error to your code will now block for the duration the server asked for and then succeed. If you have retry logic of your own wrapped around this library, you now have two layers and a multiplied backoff, so take yours out. If you have tests that assert on 429 handling or that mock a rate-limited response, expect them to hang for whatever `Retry-After` your fixture returns.

Structured logging hooks let you attach request and response metadata to your own logger rather than parsing the library's log lines.

## Suggested order

Bump Python to 3.10 and land it. Move to v2.9 and run the suite with warnings as errors. Fix the constructor first, since it is mechanical and touches the fixtures everything else runs through, then the timeouts, then `fetch_all`, and leave the dict-to-dataclass conversion for last: it is the largest diff and the one that benefits most from having a green suite underneath it. Then bump to v3, which at that point should be a version change and nothing else.