# Migrating from v2 to v3

v3 is a typing and memory-behaviour release: the constructor takes a config object, responses come back as dataclasses instead of dicts, unbounded result loading is gone, and timeouts are explicit about which phase they bound. None of these have automated fixes, so plan the work as a sequence of small mechanical passes over your call sites rather than a single upgrade commit. Most codebases spend the bulk of the effort on the dict-to-dataclass change, because it is the one that touches the most lines and the one a type checker helps with least until you have finished it.

## Upgrade in two steps, not one

There is no codemod, but v2.9 exists precisely to stand in for one. It accepts both the old and the new spelling of everything listed below and emits a `DeprecationWarning` at each call site still using the old form, so you can pin to it, turn warnings into errors, and let your test suite enumerate the work for you:

```bash
pip install 'yourlib>=2.9,<3'
python -W error::DeprecationWarning -m pytest
```

Fix warnings until the suite is clean, and commit that state — it runs correctly on both 2.9 and 3.x, which means you can ship it to production and verify it under real traffic before you take the version bump. Only then change the pin to `>=3,<4`. Skipping the intermediate release is possible but costs you the warning locations, and the failures you get instead are a mix of `TypeError` at construction, `TypeError` on timeout arguments, and `AttributeError` scattered through response handling, none of which point at each other.

One caveat on relying on the warnings: they fire only on code paths your tests actually execute. Before you declare the 2.9 stage finished, grep for the patterns directly — `fetch_all`, `timeout=`, `Client(` — since an untested error handler that passes a float timeout will not warn on 2.9 and will raise on 3.

## Move the interpreter first

Python 3.8 support is dropped and the minimum is now 3.10. Do the interpreter upgrade as its own change, before you touch the library, so that failures from `match` statements, changed `typing` behaviour, or dependencies that lag behind 3.10 do not arrive mixed in with library breakage. If you are stuck on 3.8 for reasons outside your control, the migration stops here — v2.9 still supports it, so land the deprecation fixes anyway and take the version bump when the interpreter moves.

## Constructor: positional arguments become a config object

```python
# v2
client = Client("https://api.example.com", token)

# v3
client = Client(ClientConfig.from_url("https://api.example.com", token))
```

`from_url` covers the simple case and is what most call sites should use. Where you were constructing clients repeatedly — per request, per worker, per test fixture — build the `ClientConfig` once at module or application scope and pass it around, since it is now an ordinary value with no connection state attached to it. The config is also where the timeout lives, which matters for the change two sections down: a call site that used to pass `timeout=` per call may be better expressed as a config with the timeout baked in.

## Responses are dataclasses, not dicts

Every method that returned a `dict` now returns a typed dataclass, so key access becomes attribute access:

```python
# v2
result = client.get_page(1)
for item in result["items"]:
    print(item["name"])

# v3
result = client.get_page(1)
for item in result.items:
    print(item.name)
```

Subscripting is the obvious break, but it is not the only one, and the others are easier to miss because they are spread across code that never looks like it is touching the response. Anything treating the result as a mapping stops working: `result.get("items", [])`, `"items" in result`, `**result` unpacking into a function call or a second dict, iteration over keys, and `json.dumps(result)` at a serialization boundary. For the last of these, `dataclasses.asdict(result)` gives you back a plain nested dict and is usually the smallest correct fix — though if you are serializing to an external contract, this is a good moment to write the mapping explicitly instead, since the dataclass field names are now part of an API that can change under you.

Optional fields need a decision rather than a translation. `result.get("cursor")` returning `None` for an absent key becomes a field that is either always present and typed `Optional`, in which case `result.cursor` is the direct replacement, or genuinely absent on some response variants, in which case you want `getattr(result, "cursor", None)` and a note explaining why. Once this pass is done, run mypy or pyright over the call sites; misspelled field names that used to fail as a `KeyError` at runtime become static errors, and picking them up here is most of the payoff for the change.

## `fetch_all()` is removed in favour of `iterate()`

`fetch_all()` loaded the entire result set into memory, and `iterate()` replaces it by yielding pages:

```python
# v2
for item in client.fetch_all():
    process(item)

# v3
for page in client.iterate():
    for item in page.items:
        process(item)
```

The nested loop is the point — it is what keeps memory bounded to one page — so resist flattening it back into `[item for page in client.iterate() for item in page.items]` unless you have measured the result set and know it fits. Where a genuine list is unavoidable, at least bound it explicitly with `itertools.islice` so an unexpectedly large response fails loudly instead of exhausting the host.

Be aware that laziness moves your failures. `fetch_all()` did all its network work before returning, so a network error surfaced at the call; `iterate()` does the work as you consume it, so errors now surface partway through your processing loop, after some items have already been handled. Any code that was safe because it only ran on a complete result set — truncating a table before insert, for instance — needs the transaction boundary reconsidered rather than the loop mechanically rewritten.

## Timeouts: `float` becomes `Timeout(connect=..., read=...)`

```python
# v2
client.get_page(1, timeout=5.0)

# v3
client.get_page(1, timeout=Timeout(connect=2.0, read=10.0))
```

Passing a float now raises `TypeError` instead of warning, which is the friendlier failure mode of the two — nothing gets silently reinterpreted — but it is a runtime failure, so the risk is a `timeout=` in an error-handling path that your tests never reach. Grep for it rather than trusting the suite.

Do not translate `timeout=5.0` into `Timeout(connect=5.0, read=5.0)` by reflex. The old float bounded the operation as a whole; the new values bound two phases independently, so copying the number into both roughly doubles your worst-case wall clock and can push a request past an upstream deadline that used to hold. A connect timeout wants to be short, because a connection that has not established in a couple of seconds is usually not going to; a read timeout wants to be as long as your slowest legitimate response, which for paginated endpoints may be considerably longer than the old single number. Set them from what you know about each phase, then check the total against whatever deadline your caller enforces.

## New in v3

Three additions need no migration work, and you should adopt them after the breaking changes are landed and green rather than alongside them. `AsyncClient` mirrors the sync API for `asyncio` callers. Automatic retry on HTTP 429 honours the `Retry-After` header, so the library now sleeps and retries where v2 raised immediately. Structured logging hooks let you emit request metadata into your own logging pipeline instead of parsing the library's output.

The retry behaviour deserves a second look during the upgrade even though it breaks nothing, because it changes timing in code you already have. If you wrote your own 429 backoff around v2 calls, you now have two layers retrying the same request and multiplying each other's delays — delete yours. The added sleep also lands inside your read timeout, so a request that previously failed fast under rate limiting can now sit for the full `Retry-After` interval; if you have a latency budget or a circuit breaker keyed on call duration, re-check its threshold against the new worst case.

## Checklist

- [ ] Interpreter on 3.10 or newer, landed separately
- [ ] Pinned to `>=2.9,<3`, suite passing with `-W error::DeprecationWarning`
- [ ] Grepped for `fetch_all`, `timeout=`, and `Client(` to catch untested paths
- [ ] `Client(...)` call sites converted to `ClientConfig` / `ClientConfig.from_url`
- [ ] Key access converted to attribute access, including `.get`, `in`, `**` unpacking, and JSON serialization
- [ ] `fetch_all()` replaced with `iterate()`, and transaction boundaries reviewed for partial failure
- [ ] Timeout floats replaced with `Timeout`, connect and read values chosen per phase rather than copied
- [ ] Hand-written 429 retry loops removed
- [ ] Pin moved to `>=3,<4`

If something breaks after the pin moves that the 2.9 stage did not warn about, it is worth reporting — the deprecation release is supposed to cover the full surface, and a gap in it is a bug in the upgrade path rather than something you should work around quietly.