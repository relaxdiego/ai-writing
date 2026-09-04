# Migrating from FormKit 2.x to 3.0

One change in this release can break a working form without any error at run time: validators no longer fire on every keystroke. Everything else is either automated, backwards compatible for the 3.x line, or caught immediately by a failure at startup. Read the section on validation timing before you ship, even if the upgrade appears clean.

| Change | Breaks 2.x code? | Fix |
| --- | --- | --- |
| `formkit.json` → `formkit.config.js` | Yes, at startup | `npx formkit migrate-config` |
| `strictValidation` → `validation` | No, warns until 4.0 | Rename by hand |
| Validators receive `(value, context)` | No | Optional |
| Validators run on blur and submit, not on input | Yes, silently | Set `validateOn: "input"` per field |
| Node 16 dropped | Yes, at startup | Upgrade to Node 18+ |

A reasonable order of work is: upgrade Node, run the config migration, rename `strictValidation`, then audit your forms for anything that depended on per-keystroke validation.

## Node 18 or later is required

Node 16 is no longer supported. FormKit 3.0 will refuse to start on it, so this shows up the moment you run anything rather than in production. Upgrade your local toolchain, your CI image, and your deployment runtime together; a CI image left on 16 will fail the build after a successful local upgrade.

## The configuration file becomes JavaScript

`formkit.json` is replaced by `formkit.config.js`. The reason is that configuration frequently needs computed values, and JSON has no way to express them: an API endpoint assembled from an environment variable, a theme that differs between development and production, a list built from another module's exports. Under 2.x these had to be handled by generating the JSON file as a build step or by patching the config after load.

Run the automatic conversion:

```
npx formkit migrate-config
```

It reads `formkit.json`, writes `formkit.config.js`, and handles nearly every configuration in practice. It is not guaranteed to handle all of them, so read the generated file before deleting the original. If yours is one of the cases it cannot convert, the new file is an ordinary ES module whose default export is the configuration object, and you can write it by hand:

```js
// formkit.config.js
export default {
  theme: process.env.NODE_ENV === 'production' ? 'compact' : 'default',
  endpoint: new URL('/api/forms', process.env.API_BASE).toString(),
  validation: 'strict',
}
```

## `strictValidation` becomes `validation`

The boolean `strictValidation` is replaced by `validation`, which takes `"strict"`, `"loose"`, or `"off"`. The mapping from the old values is direct:

- `strictValidation: true` becomes `validation: "strict"`
- `strictValidation: false` becomes `validation: "loose"`
- `validation: "off"` is new, and disables validation entirely. There was no way to express this in 2.x.

The boolean still works in 3.0 and emits a deprecation warning; it will be removed in 4.0. Because it keeps working, this is the change most likely to be forgotten, and the warning is the only thing standing between you and a failure at the next major version. Check `formkit.config.js` after running `migrate-config` and replace any boolean that survived the conversion.

## Validators receive a second argument

A validator used to be called with the field's value alone. It is now called with the value and a context object carrying the other field values, which makes cross-field rules expressible without reaching outside the validator for form state.

```js
// 2.x, and still correct in 3.0
const notEmpty = (value) => value.trim() !== '' || 'Required'

// 3.0: cross-field validation
const matchesPassword = (value, context) =>
  value === context.password || 'Passwords must match'
```

Nothing is required of you here. A validator that declares one parameter is unaffected by the extra argument, so existing validators keep working exactly as they did, and you adopt the context object only where you want it.

## Validators run on blur and submit, not on every keystroke

This is the breaking change with no automatic fix.

In 2.x, a field's validators ran on every input event. In 3.0 they run when the field loses focus, and again on submit. The old behaviour meant that any validator making a server-side check fired one request per character typed, which is expensive for you and slow for the user, and it made debouncing a requirement rather than an optimisation.

The visible consequence is that error messages now appear later than your users are used to, and any UI keyed to validation state changes during typing will no longer update until the field is left. Nothing throws, and no warning is printed, so this will not surface in a build or a type check. It surfaces when someone uses the form.

Where per-keystroke validation was the point, restore it on that specific field with `validateOn`:

```js
{
  name: 'coupon',
  type: 'text',
  validateOn: 'input',
}
```

This is deliberately per field rather than global. Password-strength meters, character counters, and live format hints genuinely need to run on input; almost nothing else does, and setting it everywhere reintroduces the request-per-character problem the change was made to solve.

When auditing, the cases worth finding are fields whose validator draws a conclusion that the user is meant to see while still typing. A rule that only reports whether the finished value is acceptable reads better under the new timing than it did under the old, and should be left alone.