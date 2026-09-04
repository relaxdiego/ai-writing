# Migrating to formkit 3.0

One change in 3.0 alters behaviour without an error, a warning, or a failing build: validators no longer run on every keystroke. If you have a field whose validation feedback appears as the user types, it will now appear when they leave the field, and nothing in the upgrade will tell you. Fixing it means adding `validateOn: "input"` to those fields by hand, so find them before you ship the upgrade rather than after.

Everything else is either automatic or announced. Here is the whole set:

| Change | If you do nothing | Fix |
| --- | --- | --- |
| `formkit.json` → `formkit.config.js` | The old file is no longer read | `npx formkit migrate-config` |
| `strictValidation` → `validation` | Works, prints a warning; removed in 4.0 | Rename; `true` → `"strict"`, `false` → `"loose"` |
| Validators receive `(value, context)` | One-argument validators keep working | Nothing required |
| Validators run on blur and submit | Per-keystroke validation silently stops | `validateOn: "input"` on that field |
| Node 16 dropped | Unsupported runtime | Node 18 or later |

## Before you begin: Node 18

3.0 requires Node 18 or later. Upgrade the runtime first, in local environments and in CI images alike, because the rest of the migration is easier to verify on a version the library actually supports. If your `package.json` pins an `engines` range, widen it in the same commit so contributors get the failure at install time instead of at runtime.

## The configuration file

`formkit.json` becomes `formkit.config.js`. The reason is that people needed computed values and JSON has no way to express them, so the new file is a module that exports a configuration object and can read environment variables, branch on the build target, or import shared constants.

Run the converter:

```
npx formkit migrate-config
```

It handles almost every case, and a plain settings file will come through untouched in meaning:

```js
// formkit.config.js
export default {
  theme: "default",
  locale: "en",
}
```

Read the file it produces before you delete the old one. The values are yours and the converter is mechanical, so anything unusual in the original is worth a second look. In particular, check whether `strictValidation` survived the conversion; if it is still there, rename it now as described below rather than leaving a deprecation warning in your logs.

Once the new file is committed and the application starts, delete `formkit.json`. Leaving it in the tree invites someone to edit it six months from now and wonder why nothing changes.

## `strictValidation` becomes `validation`

The boolean is replaced by a three-value string:

```js
// 2.x
{ strictValidation: true }

// 3.0
{ validation: "strict" }
```

`true` becomes `"strict"` and `false` becomes `"loose"`. The third value, `"off"`, has no 2.x equivalent; it disables validation entirely, which previously could only be approximated by removing validators. The old boolean still works in 3.0 and prints a warning at startup, and it will be removed in 4.0, so treat the warning as a deadline rather than noise.

## Validators receive a second argument

A validator used to be called with the field's value alone. In 3.0 it is called with the value and a context object carrying the other field values, which makes cross-field rules expressible without reaching outside the validator:

```js
// 2.x — still valid in 3.0, called with one argument as before
const notReserved = (value) => !RESERVED.includes(value)

// 3.0 — the second parameter carries the other fields
const matchesPassword = (value, context) => value === context.password
```

The parameter is additive and JavaScript ignores arguments a function does not declare, so every existing one-argument validator keeps working with no edit. Adopt the second argument where a rule needs it and leave the rest alone. The exact keys available on `context` are in the 3.0 API reference.

## When validators run

In 2.x, validators ran on every keystroke. In 3.0 they run when a field loses focus, and on submit.

The change was made because the old behaviour was expensive in exactly the case where validation matters most. A validator that checks a username against the server fired one request per character, so typing a twelve-character name meant twelve round trips, of which eleven were answers to questions nobody had finished asking. Blur-and-submit collapses that to one.

Where you genuinely want feedback as the user types, ask for it per field:

```js
{
  name: "coupon",
  validators: [isWellFormedCoupon],
  validateOn: "input",
}
```

Note the tension when you go looking for fields to annotate. The fields whose validation feels best on every keystroke are usually the cheap local ones: length rules, character-set rules, a format check that runs in a microsecond. The fields you are most tempted to restore are the ones with a server call behind them, and those are the ones the new default exists to protect. If a server-backed field needs live feedback, add `validateOn: "input"` and debounce the request.

There is no codemod for this and no warning at runtime, because a validator that runs later is not an error. Auditing by hand is the only reliable method: search for every field with a validator attached, and decide for each one whether blur is soon enough. On most forms it is, which is why the default changed; the exceptions are few enough to list in a commit message.

## Suggested order

1. Move to Node 18 and confirm the test suite passes on 2.x.
2. Run `npx formkit migrate-config`, review the output, delete `formkit.json`.
3. Rename `strictValidation` and confirm the startup warning is gone.
4. Upgrade to 3.0 and audit fields for `validateOn: "input"`.
5. Adopt the validator `context` parameter where a cross-field rule wants it.

Steps 1 through 3 can land on 2.x ahead of the upgrade, which keeps the release that actually changes behaviour small enough to reason about.