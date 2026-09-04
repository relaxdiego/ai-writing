# Migrating from formkit 2.x to 3.0

One change in 3.0 will not announce itself. Validators no longer run on every keystroke; they run when a field loses focus and on submit. Nothing warns you, nothing fails to compile, and forms that depended on per-keystroke feedback will simply feel different to your users. Everything else in this release either has a codemod, prints a deprecation warning, or fails loudly at install time. Budget your attention accordingly: read the section on validation timing carefully and treat the rest as mechanical.

| Change | What you have to do | How you find out |
| --- | --- | --- |
| Node 16 dropped, 18+ required | Upgrade Node | Install fails |
| `formkit.json` → `formkit.config.js` | Run `npx formkit migrate-config` | Startup error |
| `strictValidation` → `validation` | Optional in 3.0, required before 4.0 | Deprecation warning |
| Validators receive `(value, context)` | Nothing | Not applicable, old signature still works |
| Validation runs on blur, not input | Add `validateOn: "input"` where you need it | Nothing tells you |

## Node 18 or later

Support for Node 16 is gone, which went out of maintenance in September 2023. Upgrade to 18 or later before you touch anything else, since the 3.0 install will refuse to run on 16 and you will not get as far as the config migration.

## The config file becomes JavaScript

`formkit.json` is replaced by `formkit.config.js`. JSON cannot compute anything, and people were working around that with build steps and generated files to get an environment variable or a derived path into their configuration. A config file that is a module solves this directly.

Run the codemod from your project root:

```
npx formkit migrate-config
```

It reads `formkit.json` and writes `formkit.config.js`, and it handles almost every case, which is not the same as all of them. Read the file it produces before you delete the old one. A configuration of this shape:

```json
{
  "theme": "default",
  "locales": ["en", "fr"]
}
```

comes out as a module with a default export:

```js
export default {
  theme: 'default',
  locales: ['en', 'fr'],
}
```

Once the new file exists you can put real expressions in it, which is the point of the change:

```js
export default {
  theme: process.env.FORMKIT_THEME ?? 'default',
  locales: ['en', 'fr'],
}
```

## `strictValidation` becomes `validation`

The boolean `strictValidation` is now the string option `validation`, taking `"strict"`, `"loose"` or `"off"`. Pass `"strict"` where you had `true` and `"loose"` where you had `false`. The third value is new: there was no way in 2.x to turn validation off entirely, and `false` never meant that.

The old boolean still works in 3.0 and prints a deprecation warning at startup, so this is not urgent, but it is removed in 4.0. The warning is also how you find out whether the config codemod rewrote the option for you: if you see it after migrating, edit `formkit.config.js` by hand.

## Validators receive a second argument

Field validators are now called as `(value, context)`, where `context` carries the values of the other fields in the form. This is additive. A validator that declares one parameter keeps working exactly as it did, and there is nothing to change:

```js
// Unchanged in 3.0
const notEmpty = (value) => value.trim().length > 0
```

The second argument exists so that cross-field rules stop needing a closure over form state:

```js
const matchesPassword = (value, context) => value === context.password
```

## Validation now runs on blur, not on input

This is the change with no codemod and no warning. In 2.x every keystroke ran the field's validators. In 3.0 they run when the field loses focus, and again on submit.

The old behaviour was actively harmful for any validator that talks to a server. A username field checking availability against an API fired one request per character, so typing an eight-character name sent eight requests, of which seven were answers to questions nobody asked. Debouncing was possible but every application had to invent it, and most did not.

Where you genuinely want per-keystroke feedback, ask for it on that field:

```js
{
  name: 'password',
  validator: strongEnough,
  validateOn: 'input',
}
```

Password strength meters, character counters, and anything else giving live feedback as the user types are the cases that want this. Availability checks, format checks and required-field checks are the cases that do not, and they are why the default changed.

Finding the fields that need it is a reading job rather than a search job, because nothing in a 2.x codebase records the distinction. Go through your validators and ask what the user sees while typing. If a validator only ever produces a message the user acts on after they have finished the field, leave it on the new default. If its output is meant to change as the field is typed into, it needs `validateOn: "input"`. Forms whose validators are all synchronous and local will need no changes at all; the difference is only in when the message appears.