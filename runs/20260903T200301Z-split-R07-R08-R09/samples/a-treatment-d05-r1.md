# Migrating from v2 to v3

Do not upgrade straight to v3. Install v2.9 first, turn its deprecation warnings into errors, fix everything they point at, and only then move to v3. There is no codemod, and v3 removes the old spellings rather than warning about them, so a direct jump replaces a list of warnings with a pile of `TypeError`s and `AttributeError`s that surface at runtime rather than at import.

The five breaking changes, in the form you will meet them in a diff:

| Concern | v2 | v3 |
| --- | --- | --- |
| Construction | `Client(url, token)` | `Client(ClientConfig.from_url(url, token))` |
| Results | `result["items"]` | `result.items` |
| Whole result set | `client.fetch_all()` | `for page in client.iterate():` |
| Timeouts | `timeout=30.0` | `timeout=Timeout(connect=5.0, read=30.0)` |
| Python | 3.8 and up | 3.10 and up |

A single call site touching most of them at once looks like this before:

```python
client = Client("https://api.example.com", token="sk-...")
result = client.fetch_all(timeout=30.0)
for item in result["items"]:
    print(item["name"])
```

and like this after:

```python
config = ClientConfig.from_url("https://api.example.com", token="sk-...")
client = Client(config)
for page in client.iterate(timeout=Timeout(connect=5.0, read=30.0)):
    for item in page.items:
        print(item.name)
```

## Do the interpreter bump first

Move to Python 3.10 before anything else, in its own change, because it is the one step that touches CI images, deployment base images, and any tooling pinned to your minimum version, and you do not want that churn interleaved with library edits. v2.9 still runs on 3.8, so you can land the interpreter upgrade, confirm the suite is green on v2.9 under 3.10, and treat the library work as a separate reviewable change.

## Construction

`ClientConfig.from_url` covers the case where you had a URL and a token and nothing else, and it is the mechanical replacement for the old two-argument call. If you were passing other keyword arguments to `Client`, build the config directly instead of routing them through the helper, and read the `ClientConfig` fields before assuming a name carried over unchanged. Constructing the config once and reusing it across clients is now the natural way to share settings between a sync and an async client.

## Return types

Every method that returned a `dict` now returns a dataclass, so key access becomes attribute access and `.get()` calls have no direct equivalent. Two habits break in ways worth watching for: code that did `result.get("items", [])` to tolerate a missing key needs to decide what absence now means, since a dataclass field either exists or the attribute lookup raises; and code that serialised a result with `json.dumps(result)` needs `dataclasses.asdict` in front of it. Anything that iterated over keys, merged results with `**`, or passed a result into a function expecting a mapping will need rewriting rather than a find-and-replace.

This is the change I would verify against the v2.9 release notes before planning around it. The other four can be adopted while still on v2.9, so the warnings and the fixes land together; whether v2.9 can also warn on key access depends on it returning a dict subclass that reports each lookup, and if it does not, the warnings will only tell you which methods are affected and the edits themselves land at the moment you install v3. Assume the second case when scheduling the work, and treat it as good news if the first turns out to hold.

## Removing `fetch_all`

`fetch_all` loaded the entire result set into memory, and `iterate` yields pages, so the replacement is a nested loop rather than a rename. Where the old code did something that needs the whole collection, such as sorting, taking a length, or indexing, you have a choice: rebuild the list with `list(chain.from_iterable(page.items for page in client.iterate()))` and accept the memory cost you had before, or restructure the operation to work per page. Rebuilding the list is a legitimate first move for a small result set and keeps the migration mechanical; the streaming form is the reason the method changed, and it is worth taking on the paths where the result set is large or unbounded.

## Timeouts

Passing a float now raises `TypeError` at the call site rather than warning, which makes this the easiest change to find and the easiest to get subtly wrong. Copying the old number into both fields is the wrong translation: `Timeout(connect=30.0, read=30.0)` permits sixty seconds of waiting where the old `30.0` permitted thirty. Set `connect` to a few seconds, since a connection that has not been established quickly is usually not going to be, and put the old value on `read`, where the time was actually being spent.

## What arrives with v3

`AsyncClient` mirrors the sync API, takes the same `ClientConfig`, and is the reason to build the config as a separate object rather than inline. Retry on 429 is automatic and honours `Retry-After`, which changes behaviour without changing any signature: a call that previously raised on a rate limit now sleeps for the interval the server asked for and retries, so a request that used to fail in milliseconds can take a minute and read, to anything watching, like a hang. Check any wrapping timeout, health check, or request budget that assumed a fast failure. Structured logging hooks let you attach your own handlers for request and response events, which is the supported way to get the visibility that timing wrappers around the old client were providing.

## The order of work

1. Upgrade the interpreter to 3.10, on v2, and get the suite green.
2. Pin v2.9 and run the test suite with `-W error::DeprecationWarning` so a warning fails the test rather than scrolling past.
3. Fix the constructor, timeout, and `fetch_all` call sites, which can all be written in their v3 form while still on v2.9. Commit here; the suite passes on v2.9 with no warnings.
4. Move to v3 and fix the dict-to-dataclass call sites the warnings identified.

Step 4 is the one that cannot be de-risked by staying on v2.9, so budget for it as real work rather than as the final `pip install`. Its size is the number of places you read a field out of a result, which the step 2 run has already counted for you.