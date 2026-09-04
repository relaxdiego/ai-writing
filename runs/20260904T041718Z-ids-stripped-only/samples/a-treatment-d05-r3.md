# Migrating from formkit 2.x to 3.0

One change in this release can break a form without producing an error, a warning, or a failing build: validators no longer run on every keystroke. If any of your forms depend on validation firing as the user types, you have to opt back in per field with `validateOn: "input"`, and nothing in the upgrade will tell you which fields those are. Everything else in 3.0 is either converted for you or keeps working as it did. Read [When validation runs](#when-validation-runs) before you ship.

## Before you begin

Node 16 is no longer supported. Move to Node 18 or later first, on your machines and in CI, so that the rest of the upgrade runs on the version you will actually deploy against.

## The configuration file

`formkit.json` is replaced by `formkit.config.js`. JSON could not express a computed value, so anything that varied by environment had to be patched in after loading the config or duplicated across files; a JavaScript module lets the config read `process.env`, import shared constants, and branch.

Run the converter from your project root:

```
npx formkit migrate-config
```

It reads `formkit.json`, writes `formkit.config.js` beside it, and translates renamed options along the way (including `strictValidation`, below). It handles almost every 2.x config, but read the generated file before committing it, then delete `formkit.json`. If both files are present, 3.0 uses `formkit.config.js` and ignores the old one, which is a quiet way to spend an afternoon wondering why an edit had no effect.

A converted config looks like an ordinary module with a default export:

```js
// formkit.config.js
export default {
  validation: "strict",
  theme: "default",
}
```

Now that it is code, the values it exports can be computed:

```js
export default {
  validation: process.env.NODE_ENV === "production" ? "strict" : "loose",
  theme: "default",
}
```

## `strictValidation` becomes `validation`

The boolean `strictValidation` is replaced by `validation`, which takes one of three string values. The old option still works in 3.0 and prints a deprecation warning on startup; it will be removed in 4.0, so treat the warning as work to schedule rather than noise to suppress.

| 2.x | 3.0 |
| --- | --- |
| `strictValidation: true` | `validation: "strict"` |
| `strictValidation: false` | `validation: "loose"` |
| no equivalent | `validation: "off"` |

`"off"` is new. There was no way to disable validation wholesale in 2.x, and the boolean has no value that maps onto it, so `migrate-config` will never produce it. Set it yourself if you want it.

## Validators receive a second argument

Validator functions are now called with `(value, context)` rather than `(value)`. The context object carries the other field values in the form, which makes cross-field rules possible without reaching outside the validator for form state:

```js
const matchesPassword = (value, context) => value === context.password
```

This is additive. A validator declared with one parameter ignores the extra argument and behaves exactly as it did in 2.x, so there is nothing to change unless you want the context.

## When validation runs

In 2.x, validators ran on every keystroke. In 3.0 they run when a field loses focus, and again on submit. The old behaviour meant that a validator making a server-side check, such as asking whether a username is taken, sent one request per character typed; debouncing it was left to every application that hit the problem.

Where you do want per-keystroke validation, ask for it on the field:

```js
{
  name: "coupon",
  type: "text",
  validators: [isValidCoupon],
  validateOn: "input",
}
```

`validateOn: "input"` restores the 2.x timing for that field alone, and it composes with everything else: the field still validates on blur and on submit as well.

There is no codemod for this, because whether a field wants live feedback is a product decision rather than a mechanical property of the code. The practical way to find the affected fields is to work from the behaviour rather than the source. Any field whose validation drove something the user watched while typing, a password strength meter, a character counter backed by a validator, a format hint that appeared and disappeared mid-word, will now stay silent until focus leaves it. Fields that simply reject bad input on submit are unaffected and should be left on the new default.

## Upgrade checklist

- Move to Node 18 or later, including CI.
- Run `npx formkit migrate-config`, review `formkit.config.js`, delete `formkit.json`.
- Replace `strictValidation` with `validation` and silence the deprecation warning before 4.0.
- Decide whether any form wants `validation: "off"`, which is newly available.
- Walk your forms for validation that the user watched while typing, and add `validateOn: "input"` to those fields.