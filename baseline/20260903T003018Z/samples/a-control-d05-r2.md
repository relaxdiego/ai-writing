# Migrating from v2 to v3

v3 is a breaking release. Most of the work is mechanical, but there is no codemod — you will be editing call sites by hand. The path below is designed so the compiler-equivalent (deprecation warnings on v2.9) finds those call sites for you instead of your users finding them in production.

**Budget:** roughly an afternoon for a small service, a few days for a large codebase with heavy `dict` result handling.

## At a glance

| Change | v2 | v3 |
|---|---|---|
| Construction | `Client(url, token)` | `Client(ClientConfig.from_url(url, token))` |
| Results | `dict`, key access | dataclasses, attribute access |
| Bulk reads | `client.fetch_all()` | `client.iterate()` (yields pages) |
| Timeouts | `timeout=30.0` | `timeout=Timeout(connect=..., read=...)` |
| Python | 3.8+ | 3.10+ |

New in v3, nothing required of you: `AsyncClient`, automatic retry on 429 honouring `Retry-After`, and structured logging hooks.

## Do this in two steps

Go to **v2.9 first**. It is API-compatible with v2 but emits a deprecation warning for every construct listed above. Fix the warnings there, with a working test suite and a rollback that is one version pin away, then bump to v3 — which should be a no-op if you did the work.

```bash
pip install 'mylib>=2.9,<3'
```

Turn the warnings into failures so none are missed. In pytest:

```ini
# pyproject.toml
[tool.pytest.ini_options]
filterwarnings = ["error::DeprecationWarning"]
```

Or for a one-off sweep over a running app:

```bash
python -W error::DeprecationWarning -m yourapp
```

Warnings only fire on code paths that actually execute, so coverage of your client calls matters more than usual here. If a module is thinly tested, grep it directly:

```bash
grep -rn 'fetch_all\|Client(\|timeout=' --include='*.py' .
```

When the suite is green with warnings-as-errors, upgrade:

```bash
pip install 'mylib>=3,<4'
```

---

## 1. Python 3.10 minimum

Do this before anything else — it gates the rest, and it is the change most likely to involve someone other than you (base images, CI matrices, deployment targets).

If you are on 3.8, you may as well go to 3.11 or 3.12 rather than land on the new floor. Drop 3.8 and 3.9 from your CI matrix and your `requires-python`:

```toml
[project]
requires-python = ">=3.10"
```

Nothing about the client changes here, but 3.10 is where `match` statements and `X | Y` unions become available, which is handy for the result-type migration below.

## 2. Client construction

```python
# v2
client = Client("https://api.example.com", token)

# v3
client = Client(ClientConfig.from_url("https://api.example.com", token))
```

`from_url` covers the simple case and is the right call for a straight port. Once you are on v3, `ClientConfig` is also where the other settings live, so a single config object can be built once at startup and reused:

```python
config = ClientConfig.from_url(settings.api_url, settings.api_token)
client = Client(config)
```

If you have a factory or fixture that constructs clients, change it there and most call sites will fix themselves.

## 3. Results are dataclasses, not dicts

```python
# v2
result = client.get_batch(batch_id)
for item in result["items"]:
    print(item["name"])

# v3
result = client.get_batch(batch_id)
for item in result.items:
    print(item.name)
```

Plain key access is the easy part. Watch for the dict-shaped idioms that fail less obviously:

- **`result.get("items", [])`** — no `.get()` on a dataclass. If you were using it to tolerate a missing key, check whether the field is now `Optional`; if it is, `result.items or []`, and if it isn't, drop the defensiveness.
- **`"items" in result`** — becomes an attribute check, or more often nothing at all, because the field always exists now.
- **`**result` / `dict(result)`** — use `dataclasses.asdict(result)`.
- **`json.dumps(result)`** — same: `json.dumps(dataclasses.asdict(result))`.
- **Iterating keys** — `for key in result:` no longer works. If you genuinely need field names, `dataclasses.fields(result)`.

`asdict()` is the escape hatch when a result crosses into code you don't control (a serializer, a template, a logging call). It is a deep copy, so don't reach for it inside a hot loop.

This is the one change where a type checker earns its keep. If you run mypy or pyright, the v3 types will point at every stale key access without your having to execute the path.

## 4. `fetch_all()` is gone

`fetch_all()` was removed because it loaded the entire result set into memory. `iterate()` yields pages, so you get a page at a time:

```python
# v2
for item in client.fetch_all():
    process(item)

# v3
for page in client.iterate():
    for item in page.items:
        process(item)
```

You can flatten it if the nesting is awkward:

```python
from itertools import chain

items = chain.from_iterable(page.items for page in client.iterate())
for item in items:
    process(item)
```

That stays lazy. What is *not* lazy — and what you should think twice about — is the literal translation:

```python
items = [item for page in client.iterate() for item in page.items]  # reintroduces the problem
```

That is the memory behaviour `fetch_all()` was removed for. It is fine when you know the result set is small and bounded; it is not fine as a blanket find-and-replace. Where you need the whole set in memory to do something genuinely non-streaming (a sort, a join, a count of distinct values), do it deliberately and consider whether the API can filter server-side first.

Two behavioural consequences of streaming that catch people out: errors can now surface partway through iteration rather than all at once up front, so a failure may arrive after you have already processed some items; and the connection stays open across the loop, so long-running per-item work holds it open. If per-item processing is slow, buffer a page and release before processing.

## 5. Timeouts are a `Timeout` object

```python
# v2
client.get_batch(batch_id, timeout=30.0)

# v3
client.get_batch(batch_id, timeout=Timeout(connect=5.0, read=30.0))
```

Passing a float raises `TypeError` in v3 — it does not warn and coerce. On v2.9 it warns, which is how you find these.

There is no mechanical translation, because one number can't say what two numbers meant. Connecting and waiting for a response are different failures with different right answers: a connect timeout should be short (a few seconds — either the TCP handshake and TLS complete quickly or something is wrong), while a read timeout depends on how long the operation legitimately takes. A reasonable default port is to keep your old value as `read` and pick a small `connect`:

```python
DEFAULT_TIMEOUT = Timeout(connect=5.0, read=30.0)
```

Define it once in a constants module and reference it, rather than scattering literals. If you had a deliberately generous timeout for one slow endpoint, that generosity almost certainly belonged to `read` — a 120-second *connect* timeout is never what anyone wants.

Note the interaction with the new automatic 429 retry: a request that is retried can now take meaningfully longer in wall-clock terms than a single timeout suggests, since the client sleeps for `Retry-After` between attempts. If you have an outer deadline (a request handler budget, a cron slot), size it against retries, not against a single attempt.

---

## After you land on v3

None of the following is required, but this is the natural moment to pick it up.

**Drop your own 429 handling.** If you have retry loops, backoff decorators, or `Retry-After` parsing wrapped around client calls, they are now redundant and will compound with the built-in retry — two layers of backoff multiply. Delete yours.

**`AsyncClient`** mirrors the sync API, so the migration above is the same work either way. If you were considering async, doing it *after* the v3 port is finished keeps the two changes separately revertable.

**Structured logging hooks** replace whatever request logging you wired by hand.

## Checklist

- [ ] Python 3.10+ everywhere — CI matrix, base images, `requires-python`
- [ ] Pin `mylib>=2.9,<3`, run tests with `-W error::DeprecationWarning`
- [ ] `Client(url, token)` → `Client(ClientConfig.from_url(url, token))`
- [ ] Key access → attribute access; `.get()`, `**result`, `json.dumps` handled via `asdict()`
- [ ] `fetch_all()` → `iterate()`, without silently rebuilding the full list
- [ ] Floats → `Timeout(connect=, read=)`, defined once
- [ ] Type checker clean, warnings-as-errors clean
- [ ] Bump to `mylib>=3,<4`; expect no further changes
- [ ] Remove now-redundant 429 retry logic

## Troubleshooting

| Symptom | Cause |
|---|---|
| `TypeError` on a call that worked in v2 | A float timeout reached v3. Wrap it in `Timeout`. |
| `AttributeError: 'Batch' object has no attribute 'get'` | Dict idiom on a dataclass. See §3. |
| `TypeError: string indices must be integers` | `result["items"]` where `result` is now a dataclass. |
| Memory usage unchanged after dropping `fetch_all()` | The list comprehension in §4. |
| Requests take much longer than the timeout implies | Built-in 429 retry sleeping on `Retry-After`, possibly stacked with your own retry layer. |