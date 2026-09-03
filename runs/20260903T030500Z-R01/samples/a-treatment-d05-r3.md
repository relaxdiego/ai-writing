# Migrating from v2 to v3

v3 changes the constructor, the return types, the timeout API, and the minimum Python version. None of it is subtle — code that compiles under v2 will mostly fail loudly under v3 rather than change behaviour quietly. The exception is `fetch_all()`, which is gone entirely.

There is no codemod. Do the upgrade in two hops.

## The two-step path

Go to **v2.9 first**. It is the last v2 release and it emits `DeprecationWarning` for every construct listed below. Run your test suite with warnings visible:

```bash
pip install 'yourlib>=2.9,<3'
python -W error::DeprecationWarning -m pytest
```

Turning the warnings into errors is the point — otherwise they scroll past. Fix everything the warnings flag, confirm the suite is green on 2.9 with `-W error`, then install v3. If you did the first step properly the second is a version bump.

Upgrading straight to v3 also works, but you debug against tracebacks instead of warnings, and you lose the ability to ship the intermediate state to production.

## Python 3.10 minimum

3.8 is dropped. Check this before anything else, because it may gate the rest of the work:

```bash
python --version
```

If you are on 3.8 or 3.9, move the interpreter first and land that as its own change. Mixing a runtime upgrade with an API upgrade makes failures hard to attribute.

## Constructor takes a config object

```python
# v2
client = Client("https://api.example.com", "token-abc")

# v3, simple case
client = Client(ClientConfig.from_url("https://api.example.com", "token-abc"))
```

`from_url` covers the direct translation. If you were passing other options to the constructor, or building clients in more than two or three places, construct the config once and pass it around:

```python
config = ClientConfig.from_url(settings.api_url, settings.api_token)
client = Client(config)
```

Positional `Client(url, token)` raises `TypeError` in v3.

## Methods return dataclasses, not dicts

Key access becomes attribute access:

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

This is the change most likely to reach places your type checker cannot see. Watch for:

- **Serialisation.** `json.dumps(result)` no longer works. Use whatever the dataclass exposes for this — `dataclasses.asdict(result)` if nothing else.
- **`.get()` with defaults.** `result.get("items", [])` has no direct equivalent. Optional fields are typed as optional; check for `None` instead.
- **Dict idioms.** `in`, `.keys()`, `**result`, and iteration over the result all break.
- **Anything that stores results.** Caches, fixtures, and test data holding v2 dicts will not match v3 objects.

If you run mypy or pyright, do it after this step; it will find most of the call sites for you.

## `fetch_all()` is removed

`fetch_all()` accumulated every page in memory. `iterate()` yields pages instead:

```python
# v2
items = client.fetch_all()
for item in items:
    process(item)

# v3
for page in client.iterate():
    for item in page.items:
        process(item)
```

If some caller genuinely needs the whole set materialised — a sort across all results, say — write it out explicitly so the memory cost stays visible:

```python
items = [item for page in client.iterate() for item in page.items]
```

Code that did `len(client.fetch_all())` or indexed into the result needs restructuring, not a mechanical substitution.

## Timeouts are objects

Connect and read timeouts are now separate, and a float raises `TypeError` rather than warning:

```python
# v2
client.get_page(1, timeout=30.0)

# v3
client.get_page(1, timeout=Timeout(connect=5.0, read=30.0))
```

The mechanical translation of a single v2 float is to use it as the read timeout and pick a shorter connect timeout — a few seconds is usually right, since connecting either succeeds quickly or is not going to succeed. This is a good moment to check whether the numbers in your code were ever chosen deliberately.

## What you get in return

**`AsyncClient`** takes the same `ClientConfig` and mirrors the sync API with `async`/`await`. No change needed to adopt it; it is there if you want it.

**Automatic retry on 429**, honouring `Retry-After`. If you built your own rate-limit backoff around v2, look at removing it — two retry layers interact badly, and the outer one will usually just multiply the wait.

**Structured logging hooks**, which replace whatever you were doing with request/response introspection.

## Checklist

- [ ] Python ≥ 3.10
- [ ] On v2.9, suite green under `-W error::DeprecationWarning`
- [ ] All `Client(...)` calls pass a `ClientConfig`
- [ ] No `result["key"]` access on returned objects
- [ ] No `fetch_all()` callers
- [ ] All `timeout=` arguments pass `Timeout`
- [ ] Hand-rolled 429 retry logic removed
- [ ] Bump to v3