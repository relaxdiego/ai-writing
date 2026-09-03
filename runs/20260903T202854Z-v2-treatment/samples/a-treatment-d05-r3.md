# Migrating from formkit 2.x to 3.0

One change in 3.0 alters how your forms behave without producing an error or a warning: validators no longer run on every keystroke. If any part of your application depends on validation feedback appearing as the user types, it will go quiet after upgrading until you opt back in per field. Everything else in this release either converts automatically or keeps working with a deprecation warning, so start with that section and treat the rest as cleanup.

| Change | Status in 3.0 | Action needed |
| --- | --- | --- |
| Validators run on blur and submit, not per keystroke | Breaking, silent | Add `validateOn: "input"` to affected fields |
| `formkit.json` → `formkit.config.js` | Breaking | Run `npx formkit migrate-config` |
| `strictValidation` → `validation` | Deprecated, still works | Rename before 4.0 |
| Validators receive `(value, context)` | Backwards compatible | None |
| Node 16 | Unsupported | Upgrade to Node 18 or later |

## Node 18 or later is required

Support for Node 16, which reached end of life in September 2023, has been dropped. Upgrade your runtime and your CI images before you touch anything else, because the 3.0 package will not install on 16 and you will not get far enough to see the other changes.

## Validation timing

In 2.x a field's validators ran on every keystroke. In 3.0 they run when the field loses focus, and again on submit. The old behaviour was a poor fit for validators that call a server: a username-availability check on a twelve-character name fired twelve requests, each one racing the last, and the result the user saw depended on which response happened to arrive last. Blur gives you one request per field, at the moment the user has finished typing into it.

Where you genuinely want feedback as the user types, ask for it on that field:

```js
{
  name: "password",
  validators: [minLength(12), hasSymbol],
  validateOn: "input",
}
```

There is no automatic fix for this one, because nothing in the source distinguishes a validator that wants per-keystroke feedback from one that merely tolerated it. The fields that usually want `validateOn: "input"` are the ones whose validation is cheap and whose feedback is a live indicator rather than a verdict: password strength meters, character counters, format masks, and confirm-password fields that should turn green the moment the two match. Fields backed by a network call are the ones that most benefit from the new default, so leave those alone. A search for `validators` across your form definitions is the practical way to build the list; there is no runtime warning to lean on, so this pass has to be deliberate.

## The configuration file

Configuration moves from `formkit.json` to `formkit.config.js`. JSON could not express a computed value, which meant anything conditional on the environment had to be smuggled in through a build step or a wrapper. The new file is an ES module that default-exports the same object, so you can read `process.env`, import shared constants, and branch:

```js
export default {
  locale: process.env.FORMKIT_LOCALE ?? "en",
  validation: process.env.NODE_ENV === "production" ? "strict" : "loose",
}
```

Run `npx formkit migrate-config` in the directory containing `formkit.json`. It writes `formkit.config.js`, leaves the original in place, and handles essentially every configuration we have seen. Read the output and delete the old file once you are satisfied. If the converter reports something it could not translate, the untranslated keys are the ones worth checking by hand rather than a sign that the whole file is suspect.

## `strictValidation` becomes `validation`

The boolean is replaced by a three-valued string option. `strictValidation: true` becomes `validation: "strict"`, and `false` becomes `validation: "loose"`. The third value, `"off"`, disables validation entirely and has no equivalent in 2.x; it is useful for a form that validates server-side only, or for a preview mode where you want the form rendered but inert.

The old boolean still works in 3.0 and prints a deprecation warning at startup. It will be removed in 4.0, so rename it while you are in the file. Note that `migrate-config` carries the option across as it finds it, so a converted config may still contain `strictValidation` and still warn.

## Validator arguments

Validators are now called with `(value, context)`, where `context` exposes the current values of the other fields in the form. This is additive: a validator declared with one parameter receives exactly what it received before and needs no change. The new argument replaces the pattern of closing over a form reference to reach a sibling field, which is what cross-field rules such as password confirmation previously required:

```js
const matchesPassword = (value, context) =>
  value === context.values.password || "Passwords do not match"
```