# Migrating to formkit 3.0

One change in 3.0 has no automatic fix and will change what your users see: validators no longer run on every keystroke. They now run when a field loses focus and on submit. Everything else in this release is either converted by a codemod or keeps working untouched.

| Change | How to handle it | When it bites |
|---|---|---|
| Node 16 dropped, 18+ required | upgrade your runtime and CI | 3.0 |
| `formkit.json` → `formkit.config.js` | `npx formkit migrate-config` | 3.0 |
| `strictValidation` → `validation` | rename; old boolean still works with a warning | removed in 4.0 |
| Validators receive `(value, context)` | nothing; one-argument validators are unchanged | never |
| Validation runs on blur and submit, not on input | manual: add `validateOn: "input"` per field | 3.0 |

## Before you start: Node 18

Node 16 is no longer supported. Upgrade your local runtime, your CI images, and any deployment target before you install 3.0, since the package will not run on 16 at all. This is the one step with no deprecation period.

## Step 1: convert the configuration file

Configuration moves from `formkit.json` to `formkit.config.js`. JSON could not express computed values, so anything you wanted to derive from an environment variable or share with the rest of your build had to be duplicated or generated. The new file is an ordinary module:

```js
// formkit.config.js
export default {
  theme: process.env.FORMKIT_THEME ?? 'default',
  validation: 'strict',
}
```

Run the converter and let it write the new file for you:

```
npx formkit migrate-config
```

It handles almost every configuration we have seen, but read the generated file before you commit it. It is a normal diff review: confirm every key from the old file survived, and confirm the values are what you expect. Delete `formkit.json` once you are satisfied.

## Step 2: rename `strictValidation`

The boolean becomes a three-value option, `validation: "strict" | "loose" | "off"`. Translate it directly:

| 2.x | 3.0 |
|---|---|
| `strictValidation: true` | `validation: "strict"` |
| `strictValidation: false` | `validation: "loose"` |

If the converter left `strictValidation` in your new config file, rename it by hand. The old key still works in 3.0 and prints a deprecation warning at startup; it is removed in 4.0, so clearing it now costs one line and saves you the upgrade later.

Note that `false` maps to `"loose"` and not to `"off"`. There was no way to turn validation off in 2.x, so nothing in your old config should ever become `"off"`, and the converter will never produce it. It exists for cases where you want validation disabled outright rather than relaxed.

## Step 3: decide which fields still need per-keystroke validation

This is the step that needs your judgement, and the only one where doing nothing can leave you with a working build and a worse form.

In 2.x, a field's validators ran on every keystroke. That made forms with server-side checks fire one request per character typed, which is why the default changed: validators now run when the field loses focus, and again on submit. For most fields this is an improvement, because the user is no longer told their email address is invalid while they are halfway through typing it.

Some fields genuinely need the old behaviour. Password strength meters, character counters, and any inline feedback that is meant to appear as the user types will now sit silent until the field is blurred. Restore per-keystroke validation on those fields individually:

```js
{
  name: 'password',
  validateOn: 'input',
  // ...
}
```

To find the candidates, look for fields whose validators produce feedback the user is meant to read while typing, and for anything downstream of a validator that renders continuously. Fields whose validators call the network are the ones to leave alone: they are precisely what the new default protects, and setting `validateOn: "input"` on them reinstates the request-per-character problem.

There is no warning for this change. A field that quietly stopped validating on input looks identical to one that never did, so the audit has to happen before you ship rather than after.

## Validator context

Validators are now called with `(value, context)`, where `context` carries the other field values on the form. Nothing is required of you here: a validator declared with one parameter is called exactly as before and continues to work for the life of 3.x.

The second argument removes the usual workaround for cross-field rules, which was to reach for form state from outside the validator:

```js
// 2.x and 3.0 both fine
const required = (value) => value !== ''

// 3.0: compare against another field directly
const matchesPassword = (value, context) => value === context.password
```

Adopt it where it simplifies a rule you already have, and leave the rest alone.