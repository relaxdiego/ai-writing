# Migrating from v2 to v3

Version 3 changes how a client is constructed, what its methods return, how results are paged, and how timeouts are expressed, and it drops Python 3.8. None of it is mechanical enough for a codemod, but almost all of it can be found for you: version 2.9 emits a deprecation warning at every call site that v3 will break. The recommended route is to upgrade to 2.9 first, run your test suite with deprecation warnings turned into errors, fix what surfaces, and only then move to 3.0. Code that runs warning-free under 2.9 should run unchanged under 3.0, with the exception of the interpreter requirement, which 2.9 cannot warn you about.

## Step one: get onto Python 3.10

Do the interpreter move on its own, before touching the library, because v3 will not install on 3.8 or 3.9 and you do not want a failed install masking a real incompatibility. Bump the floor in your packaging metadata (`requires-python = ">=3.10"`), drop the older interpreters from your CI matrix, and get a green build on 3.10 with the library still pinned at v2. If you are still on 3.8 in production, this is usually the longest part of the migration and the part with the fewest library-specific decisions in it.

## Step two: pin 2.9 and make the warnings loud

Pin to `>=2.9,<3` and run your tests with `-W error::DeprecationWarning`, or add `filterwarnings = ["error::DeprecationWarning"]` to your pytest config. Python silences deprecation warnings by default outside of `__main__`, so without this the 2.9 step tells you nothing. Each failure now points at a line that v3 would break, and you can fix them one at a time against a library that still accepts both forms.

## Constructing the client

The two positional arguments are replaced by a single configuration object, and the simple case has a helper so that nothing is lost in the translation:

```python
# v2
client = Client("https://api.example.com", token)

# v3
client = Client(ClientConfig.from_url("https://api.example.com", token))
```

Anything else you were passing to the constructor now belongs on the config object rather than in the call, so build the `ClientConfig` directly instead of using `from_url` once you have more than a URL and a token to supply. Application code that constructs clients in several places benefits from doing this once and passing the config around, since a `ClientConfig` is inert and cheap to share in a way that a live client is not.

## Return values are dataclasses

Every method that returned a `dict` now returns a typed dataclass, and key access becomes attribute access: `result["items"]` becomes `result.items`. The straightforward rewrites are easy to spot, but three habits around dicts fail less obviously. `result.get("items", [])` has no equivalent and must become a real attribute read, with the absent case expressed as an optional field rather than a default. Serialisation that relied on passing the result straight to `json.dumps` needs `dataclasses.asdict(result)` in between. Most treacherously, a loop written as `for key, value in result.items():` will not raise a `KeyError` that points at the problem; if the dataclass has an `items` field, the expression now evaluates to your data and fails with a `TypeError` about a list not being callable. Search for `.items()`, `.keys()` and `.values()` on library results specifically, because the type checker will catch these on 3.10 with the new annotations in place and the runtime error will not be self-explanatory.

## Paging replaces `fetch_all`

`fetch_all()` is gone because it materialised the entire result set in memory. `iterate()` replaces it, and the important detail is that it yields pages rather than individual records:

```python
# v2
for item in client.fetch_all():
    handle(item)

# v3
for page in client.iterate():
    for item in page:
        handle(item)
```

If you would rather not nest, `itertools.chain.from_iterable(client.iterate())` gives you a flat iterator of items. Resist the reflex to write `list(client.iterate())` as a quick equivalence: it reintroduces exactly the memory profile the change was made to remove, and it gives you a list of pages rather than a list of items, so it is not even a drop-in replacement.

## Timeouts

A float is no longer accepted anywhere a timeout is taken, and passing one raises `TypeError` rather than warning at runtime under v3. Connect and read durations are now separate:

```python
# v2
client.request(..., timeout=30.0)

# v3
client.request(..., timeout=Timeout(connect=5.0, read=30.0))
```

When splitting an existing single value, keep it as the read timeout and choose a much shorter connect timeout independently. A connection that has not been established in a few seconds is not going to be established, and giving it the same generous budget as a slow query is what made the single-value form a poor fit in the first place.

## What v3 adds

Once you are on 3.0, `AsyncClient` mirrors the synchronous API and takes the same `ClientConfig`, so an async migration is a separate and much smaller piece of work than this one. Retries on HTTP 429 are automatic and honour `Retry-After`, which means any hand-rolled rate-limit backoff wrapped around your v2 calls should be removed rather than left to compound with the built-in behaviour. Structured logging hooks let you attach request and response metadata to your own logger instead of scraping it from the library's output.