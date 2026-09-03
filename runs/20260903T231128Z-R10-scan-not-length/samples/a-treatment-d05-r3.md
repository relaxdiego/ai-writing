# Migrating from formkit 2.x to 3.0

One change in 3.0 will break a working form with no error and no warning: validators no longer run on every keystroke. They run when a field loses focus, and on submit. If any of your forms depend on per-keystroke feedback, you have to opt back into it field by field, and nothing in the upgrade will tell you which fields those are. Everything else in this release is either converted for you by a codemod or keeps working with a deprecation warning.

| Change | Affects | Automatic fix | Deadline |
| --- | --- | --- | --- |
| Node 16 dropped, 18+ required | Runtime | None | 3.0 |
| `formkit.json` → `formkit.config.js` | Config | `npx formkit migrate-config` | 3.0 |
| `strictValidation` → `validation` | Config | None; old form warns | Removed in 4.0 |
| Validators receive `(value, context)` | Your code | None needed | No deadline |
| Validation runs on blur, not input | Your forms | None | 3.0 |

## Before you start

Move to Node 18 or later. Node 16 is no longer supported, and this is a hard requirement rather than a deprecation, so settle it before you touch the configuration file. If your CI images or deployment targets are still pinned to 16, upgrading those is the first task in the migration and not a follow-up to it.

## The configuration file

`formkit.json` becomes `formkit.config.js`. The reason is that people kept needing to compute configuration values, reading an environment variable, deriving a URL, branching on the build target, and JSON gives you no way to do any of it. A JavaScript module gives you the whole language.

Run the converter:

```
npx formkit migrate-config
```

It handles almost every case, so treat a clean run as the expected outcome and a failure as something to read carefully rather than work around. What it produces is an ordinary module with a default export:

```js
// formkit.config.js
export default {
  theme: 'default',
  locale: 'en',
}
```

Once the file is JavaScript you can compute the values that pushed you to want this in the first place:

```js
export default {
  theme: process.env.FORMKIT_THEME ?? 'default',
  apiBase: new URL('/forms', process.env.API_ORIGIN).toString(),
}
```

Read the generated file before you delete the old one. The codemod translates the format; the option rename described in the next section is a separate matter, and if `strictValidation` survives the conversion it is still valid input in 3.0, so nothing will fail loudly to draw your attention to it.

## `strictValidation` becomes `validation`

The boolean is replaced by a three-value option, because two states turned out not to be enough:

```js
// 2.x
{ strictValidation: true }

// 3.0
{ validation: 'strict' }
```

`true` becomes `"strict"` and `false` becomes `"loose"`. The third value, `"off"`, has no 2.x equivalent; there was previously no way to express it, so nothing you can write today should translate to it. Pick it only where you actually want validation disabled rather than relaxed.

The old boolean still works in 3.0 and prints a deprecation warning when it is read. It will be removed in 4.0, so the warning is the only notice you get and the change itself is a one-line edit. Do it while you are already in the file.

## Validators now receive a context argument

Field validators used to be called with `(value)` and are now called with `(value, context)`, where `context` carries the other field values. This is additive. A validator that declares one parameter is called the same way it always was and needs no change:

```js
// Valid in 2.x and 3.0, untouched
const notEmpty = (value) => value.length > 0 || 'Required'
```

The second argument matters when a field's validity depends on another field, which previously meant reaching outside the validator for state it had no clean access to:

```js
const matchesPassword = (value, context) =>
  value === context.password || 'Passwords do not match'
```

There is nothing to migrate here. It is worth knowing about because it often removes a workaround you wrote in 2.x and can now delete.

## Validation runs on blur and submit

This is the change with no automatic fix, and the one to plan time for.

In 2.x every keystroke triggered validation. In 3.0 a field validates when it loses focus, and again on submit. The behaviour changed because the old model made any form with a server-side check fire one request per character typed, which is expensive for you and slow for the person filling in the form.

Where you genuinely want validation on every keystroke, ask for it on the field:

```js
{
  name: 'username',
  validateOn: 'input',
}
```

The work is in finding the fields that need it, since the upgrade cannot detect the dependency and the symptom is silent: the form still works, it just stops giving feedback until focus moves. Two cases are worth checking directly. The first is anything with a live indicator, a password-strength meter, a character counter driven by validation, an availability check that shows a tick as you type. The second is any test that types into a field and asserts on an error message without blurring first; those will fail, and a failing test is the cheapest way to find one of these, so run the suite early rather than after you have finished the rest of the migration.

For the fields that were doing a network round trip on every character, leaving the new default in place is the point of the change.