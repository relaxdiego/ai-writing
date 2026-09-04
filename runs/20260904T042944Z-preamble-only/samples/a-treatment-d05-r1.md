# Migrating from formkit 2.x to 3.0

Most of this upgrade is mechanical, but one change alters runtime behaviour silently and has no automatic fix: validators no longer run on every keystroke. If any of your forms depend on per-character validation, read the section on validation timing before you upgrade, because nothing errors and nothing warns when the behaviour changes underneath you.

| Change | 2.x | 3.0 | Handled for you |
| --- | --- | --- | --- |
| Config file | `formkit.json` | `formkit.config.js` | Yes, `npx formkit migrate-config` |
| Validation strictness | `strictValidation: true \| false` | `validation: "strict" \| "loose" \| "off"` | Old form still works in 3.0, warns, removed in 4.0 |
| Validator signature | `(value)` | `(value, context)` | Yes, one-argument validators are unchanged |
| Validation trigger | Every keystroke | Blur and submit | No, see below |
| Node | 16 or later | 18 or later | No |

## Requirements

Upgrade Node before you touch anything else. Node 16 is no longer supported, so do the runtime bump first and confirm your test suite still passes on Node 18 or later while you are still on formkit 2.x. Keeping the two changes separate means that when something breaks you know which upgrade caused it.

## The configuration file

`formkit.json` becomes `formkit.config.js`. JSON could not express a computed value, so anything that varied by environment had to be patched in after loading the config or duplicated across files; a JavaScript module removes that restriction.

Run the converter from your project root:

```
npx formkit migrate-config
```

It reads `formkit.json`, writes `formkit.config.js` beside it, and is expected to handle almost every configuration. Read the file it produces before you commit, then delete `formkit.json` and commit both changes together. If the converter reports anything it could not translate, that part is left for you to write by hand. One thing worth checking in the output: if a `strictValidation` key survived the conversion, rename it using the mapping in the next section rather than leaving it to warn at runtime.

A converted file looks like this:

```js
// formkit.config.js
export default {
  theme: "compact",
  locale: "en-US",
  validation: "strict",
}
```

Once it is JavaScript, the values can be computed, which is the reason for the move:

```js
const isProd = process.env.NODE_ENV === "production"

export default {
  theme: "compact",
  locale: await loadLocale(),
  validation: isProd ? "strict" : "loose",
}
```

## `strictValidation` becomes `validation`

The boolean is replaced by a three-valued string, because the old flag had no way to say "do not validate at all".

| 2.x | 3.0 |
| --- | --- |
| `strictValidation: true` | `validation: "strict"` |
| `strictValidation: false` | `validation: "loose"` |
| no equivalent | `validation: "off"` |

The boolean is still accepted in 3.0 and behaves as it always did, but it prints a deprecation warning on startup and will be removed in 4.0. There is no behaviour change hiding in the rename: `true` and `"strict"` do the same thing, as do `false` and `"loose"`. The new `"off"` value is the only genuinely new capability, and nothing in your 2.x config can have been relying on it.

## Validators receive a context argument

Field validators used to be called with the field's value alone and are now called with the value and a context object carrying the other field values:

```js
// 2.x and still valid in 3.0
const isLongEnough = (value) => value.length >= 8 || "Too short"

// 3.0
const matchesPassword = (value, context) =>
  value === context.password || "Passwords do not match"
```

This is additive. A function that declares one parameter simply ignores the second argument it is passed, so every validator you already have keeps working without modification. The change matters only when you write a new validator that needs to see another field, which previously meant reaching outside the validator for the form state.

## Validation timing

This is the change that needs your judgement, and the one place where an upgraded form can behave differently without telling you.

In 2.x, validators ran on every keystroke. In 3.0 they run when a field loses focus, and again on submit. The old behaviour was untenable for any validator that talks to a server: a username-availability check fired one request per character typed, so a twelve-character username meant twelve round trips, arriving out of order and racing each other to set the error message.

After upgrading, a form whose validation was tuned for live feedback will still submit correctly and still reject bad input. It will just stop showing errors as the user types, which is the kind of regression that passes a test suite and gets reported by a user three weeks later. Go through your fields and decide deliberately which ones need the old behaviour. Password strength indicators, character counters wired to a validation rule, and format masks that correct input as it is entered are the usual cases.

Where you want per-keystroke validation, ask for it on that field:

```js
{
  name: "password",
  type: "password",
  validateOn: "input",
  validation: [isLongEnough, hasNumber],
}
```

Set it per field rather than globally. Applying it everywhere reinstates the request storm on exactly the server-backed fields the new default exists to protect.

## Order of work

1. Move to Node 18 or later on formkit 2.x, and confirm the suite passes.
2. Install formkit 3.0.
3. Run `npx formkit migrate-config`, review `formkit.config.js`, delete `formkit.json`.
4. Replace any surviving `strictValidation` with the corresponding `validation` string.
5. Walk the field definitions and add `validateOn: "input"` to the fields that need live feedback.
6. Leave your existing validators alone; adopt the `context` argument only where a new rule needs another field's value.

Steps 1 through 4 are safe to verify by running the application and watching for deprecation warnings on startup. Step 5 has no warning to watch for, so it has to be checked by using the forms.