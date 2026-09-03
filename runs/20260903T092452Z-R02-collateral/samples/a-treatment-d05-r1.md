# Migrating from v2 to v3

Upgrade through v2.9 first. There is no codemod, and v3 turns every one of these changes into a hard error at once; v2.9 turns the same changes into deprecation warnings you can fix while your test suite still passes. The sequence:

1. Move to Python 3.10 or later.
2. Pin to v2.9 and run your test suite with `-W error::DeprecationWarning`.
3. Fix every warning. At that point your code is v3-compatible.
4. Bump to v3.

Running the warnings as errors is what makes the middle step worth taking. Left as warnings they scroll past in CI output, and you arrive at step 4 with the same pile of breakage you were trying to avoid.

## Python 3.10 is the floor

Nothing else can proceed until this is done. v3 does not install on 3.8 or 3.9, so if you are on 3.8 this is the long pole in the migration and it is entirely outside the library. Do it before you touch any call sites.

## Constructing a client

`Client(url, token)` is gone; the constructor takes a single `ClientConfig`. For the common case the helper is a one-line change:

```python
# v2
client = Client("https://api.example.com", token)

# v3
client = Client(ClientConfig.from_url("https://api.example.com", token))
```

Anywhere you were threading a URL and token as a pair through your own code, the config object is now the thing to pass around instead. It is also what `AsyncClient` accepts, so a single config can back both.

## Results are dataclasses, not dicts

Key access becomes attribute access throughout:

```python
# v2
for item in result["items"]:
    print(item["name"])

# v3
for item in result.items:
    print(item.name)
```

The mechanical substitution is easy to grep for. What is easy to miss is everything else you were doing to those dicts, because dataclasses do not support it:

- `result.get("items", [])` has no equivalent. Fields that may be absent are now typed as optional and are always present as attributes, so read them directly and check for `None`.
- `json.dumps(result)` fails. Use `dataclasses.asdict(result)` first.
- `**result` unpacking, `in` membership tests, and iteration over keys all fail. `asdict()` covers these too, though at that point consider whether the surrounding code should be reading typed fields instead.

Serialisation is the usual source of surprises here, since it tends to sit at the edges of an application where tests are thinnest.

## `fetch_all()` is removed

Use `iterate()`, which yields pages rather than materialising the whole result set:

```python
# v2
for item in client.fetch_all():
    process(item)

# v3
for page in client.iterate():
    for item in page.items:
        process(item)
```

A flattening comprehension gives you the old list back, and there are legitimate reasons to want one, such as sorting across the full set:

```python
all_items = [item for page in client.iterate() for item in page.items]
```

Understand that this reinstates exactly the memory behaviour `fetch_all()` was removed for. If the result set is large, push the work inside the loop instead.

## Timeouts are objects

A float no longer works, and unlike the other changes this one raises `TypeError` in v3 rather than degrading quietly:

```python
# v2
client.get(path, timeout=30.0)

# v3
client.get(path, timeout=Timeout(connect=5.0, read=30.0))
```

Splitting one number into two is a judgment call rather than a translation. A reasonable default is to keep your old value as `read` and give `connect` something short, in the region of 5 seconds, since a connection that has not been established by then is usually not going to be. Note that the old float was a single budget covering both phases, so the new pair is a longer worst case than the number it replaces. If you have tests asserting on elapsed time, they will need adjusting.

## Behaviour that changes without an API change

v3 retries automatically on 429 and honours `Retry-After`. This is a non-breaking addition in the sense that no signature changes, but a call that previously failed fast against a rate limit will now sleep and succeed instead. Two places feel it: tests that mock a 429 and assert an exception, which will now hang for the length of the server's `Retry-After`; and any code with its own retry loop around the client, which is now retrying a retry. Remove your loop.

## What you gain

`AsyncClient` mirrors the sync API and takes the same `ClientConfig`, so an async port is a matter of the call sites rather than the setup. Structured logging hooks let you attach a handler and receive request and response records as data instead of parsing formatted lines. Neither requires any change to working v3 code, so leave both until after the migration is green.