# Migrating from formkit 2.x to 3.0

## Validators no longer run on every keystroke

This is the only change in 3.0 that alters how your forms behave without telling you, and it has no automatic fix.

In 2.x, a field's validators ran on every keystroke. In 3.0 they run when the field loses focus, and again on submit. The old behaviour was expensive for anyone validating against a server: a validator that checks whether a username is already taken fired one request per character typed, so a ten-character name cost ten round trips and the answers arrived out of order. If a field genuinely needs per-keystroke feedback, such as a password-strength meter or a live character count, set `validateOn` on that field to restore the 2.x timing:

```js
{
  name: 'password',
  validateOn: 'input',
}
```

Go through your forms field by field before you upgrade. Nothing will error, and nothing will warn; validation messages will simply appear later than they used to, which is easy to miss in a test suite that fills a field and asserts immediately.

## Node 18 or later is required

Support for Node 16 is dropped. Check your CI images, your Dockerfiles and any `engines` field before upgrading the package, since a Node 16 runtime will fail at install rather than at runtime.

## The configuration file becomes `formkit.config.js`

`formkit.json` is replaced by `formkit.config.js`, which exports the configuration object. The move exists because configuration values often need to be computed, and JSON offers no way to read an environment variable, branch on the build target, or share a constant with the rest of the project.

Run the converter from the root of your project:

```
npx formkit migrate-config
```

It reads `formkit.json` and writes `formkit.config.js` alongside it. Option names carry over unchanged apart from `strictValidation`, described below, which the converter also rewrites. It is expected to handle almost every configuration, but read the generated file before you delete the original, particularly if your old config was assembled by a build step rather than written by hand.

The new file is ordinary JavaScript, so values can be computed:

```js
// formkit.config.js
export default {
  validation: 'strict',
  apiUrl: process.env.FORMKIT_API_URL ?? 'http://localhost:3000',
}
```

## `strictValidation` becomes `validation`

The boolean `strictValidation` is replaced by a three-valued `validation` option. `true` becomes `"strict"` and `false` becomes `"loose"`; `"off"` is new and disables validation entirely, which 2.x had no way to express.

```js
// 2.x
{ strictValidation: true }

// 3.0
{ validation: 'strict' }
```

The old option still works in 3.0 and prints a deprecation warning on startup. It is removed in 4.0, so treat the warning as a task rather than noise.

## Validators receive a second argument

Field validators used to be called with `(value)` and are now called with `(value, context)`, where `context` carries the values of the other fields. One-argument validators keep working exactly as they did; JavaScript ignores the extra argument, so there is nothing to change unless you want the new capability.

```js
// 2.x, still correct in 3.0
const notEmpty = (value) => value.trim().length > 0

// 3.0: cross-field validation without reaching outside the form
const matchesPassword = (value, context) =>
  value === context.values.password
```

This mainly replaces whatever workaround you were using for confirm-password and date-range fields, which in 2.x had to read form state from a closure or from the DOM.

## Checklist

| Change | Automatic fix | Acts by |
| --- | --- | --- |
| Node 16 dropped | None; upgrade the runtime | 3.0 |
| `formkit.json` → `formkit.config.js` | `npx formkit migrate-config` | 3.0 |
| Validation runs on blur and submit | None; add `validateOn: "input"` per field | 3.0 |
| `strictValidation` → `validation` | Handled by `migrate-config`; old option warns | 4.0 |
| Validator signature `(value, context)` | Nothing to do | — |

One assumption to correct if it is wrong: I have written the cross-field example as `context.values.<fieldName>`, since the exact accessor was not specified.