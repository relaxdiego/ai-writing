# Migrating from formkit 2.x to 3.0

One change in this release can break a working form without producing an error: validators no longer run on every keystroke. Everything else is either handled by a command or keeps working as-is, so read that section first even if you skip the rest.

| Change | What you do | Fails loudly? |
| --- | --- | --- |
| Validators run on blur and submit, not per keystroke | Add `validateOn: "input"` to fields that need it | No. The form still works; feedback just arrives later |
| `formkit.json` becomes `formkit.config.js` | Run `npx formkit migrate-config` | Yes. 3.0 will not find your config |
| `strictValidation` becomes `validation` | Rename the option | Warning in 3.0, removed in 4.0 |
| Validators receive `(value, context)` | Nothing | Not applicable; one-argument validators are unchanged |
| Node 16 dropped | Move to Node 18 or later | Yes, at install |

## Validation timing

In 2.x a validator ran on every input event. In 3.0 it runs when the field loses focus, and again on submit. The old behaviour meant that a validator making a server-side check fired one request per character typed, which is why the default changed.

Nothing throws when you upgrade. The validator still runs, still returns the same result, and still blocks submission. What changes is when the user sees the message, so the failure mode is a form that feels different rather than one that reports an error. To restore the old behaviour on a field, set `validateOn`:

```js
{
  name: 'username',
  validate: (value) => value.length >= 3 || 'Too short',
  validateOn: 'input',
}
```

Three places are worth checking before you decide you have no per-keystroke validators. Anywhere you show live feedback as the user types, such as a password strength meter or an email format hint, needs `validateOn: "input"` to keep working. Anywhere you wrapped a validator in a debounce or throttle, you were working around the old default: leave the new default in place and delete the wrapper rather than adding `validateOn: "input"` back. And your test suite will tell you about the rest, though not in a form you can read at a glance: any test that types into a field and asserts on an error message without blurring first will now fail. Those failures are correct, and the fix is to blur the field in the test, or to set `validateOn: "input"` if the live feedback is the behaviour under test.

## The configuration file

`formkit.json` is replaced by `formkit.config.js`, so that values can be computed instead of written out as literals. Run the migration from your project root:

```
npx formkit migrate-config
```

It reads `formkit.json` and writes `formkit.config.js`, and it handles almost every configuration. Review the generated file and run your build before you delete `formkit.json`; committing the conversion on its own makes the diff easy to read and easy to revert.

The point of the move is that the config is now a module, so anything you previously had to hardcode or template at build time can be computed:

```js
// formkit.config.js
export default {
  endpoint: process.env.FORMKIT_ENDPOINT ?? '/api/forms',
  validation: 'strict',
}
```

Use `module.exports` instead of `export default` if your project is CommonJS.

## `strictValidation` becomes `validation`

The boolean is replaced by a three-value option. The old name still works in 3.0 and prints a deprecation warning; it is removed in 4.0.

| 2.x | 3.0 |
| --- | --- |
| `strictValidation: true` | `validation: "strict"` |
| `strictValidation: false` | `validation: "loose"` |
| No equivalent | `validation: "off"` |

`"off"` is new and has no 2.x counterpart, so the migration is a pure rename. After running `migrate-config`, check whether the generated file still uses `strictValidation` and rename it there.

## Validators receive a context argument

Validators are now called as `(value, context)`, where `context` holds the other field values. This is additive: a validator declared with one parameter ignores the second argument and behaves exactly as it did in 2.x, so there is nothing to migrate.

What it buys you is cross-field validation without reaching outside the validator for the other values:

```js
{
  name: 'confirmPassword',
  validate: (value, context) =>
    value === context.password || 'Passwords do not match',
}
```

## Node 18

Node 16 is no longer supported. Check `node --version` locally, then the places that pin a version independently of your machine: CI runner images, Dockerfiles, and the `engines` field in `package.json`.

## Suggested order

1. Move to Node 18 or later and confirm the 2.x app still builds and passes on it. This isolates any Node-related breakage from the formkit upgrade.
2. Install 3.0 and run `npx formkit migrate-config`. Review the generated file, build, then remove `formkit.json`.
3. Rename `strictValidation` to `validation`, mapping `true` to `"strict"` and `false` to `"loose"`.
4. Run your test suite. Fix the validation-timing failures by blurring in the test, or by adding `validateOn: "input"` where live feedback is the intended behaviour.
5. Walk through the forms that show feedback as the user types. These are the ones your tests are least likely to cover and the ones users will notice.