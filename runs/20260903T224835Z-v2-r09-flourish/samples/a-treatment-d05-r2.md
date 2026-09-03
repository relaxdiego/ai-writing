# Migrating from formkit 2.x to 3.0

Validators no longer run on every keystroke. This is the one change in 3.0 that will alter the behaviour of forms you have not touched, and it is the one change with no automatic fix; if any of your fields depend on validating as the user types, you have to opt them back in by hand. Everything else in this release is either converted for you by a command or kept working unchanged for the whole 3.0 line.

## At a glance

| Change | Status in 3.0 | What you do |
| --- | --- | --- |
| Node 16 dropped | Hard requirement | Upgrade to Node 18 or later before installing |
| Validation timing | Behaviour changed | Add `validateOn: "input"` to fields that need per-keystroke checks |
| `formkit.json` → `formkit.config.js` | Old file no longer read | Run `npx formkit migrate-config`, then review the result |
| `strictValidation` → `validation` | Old option works, warns | Replace at your convenience; removed in 4.0 |
| Validator signature | Additive | Nothing, unless you want the new `context` argument |

## Before you start: Node 18

Node 16 is no longer supported. Upgrade your local toolchain and your CI images to Node 18 or later before you install 3.0, because the failure mode if you skip this is an install-time or runtime error rather than a clear message about versions.

## Validation timing

In 2.x, a field's validators ran on every keystroke. In 3.0 they run when the field loses focus, and again on submit. The reason for the change is that per-keystroke validation made any form with a server-side check fire one request per character typed, which is expensive for you and slow for the user.

Nothing in your code will error because of this; the forms will simply validate later than they used to. Where you want the old behaviour, ask for it on the field:

```js
{
  name: 'username',
  validators: [notEmpty, noSpaces],
  validateOn: 'input',
}
```

Go through your forms and look for the cases that genuinely depended on the old timing: password-strength meters, character counters driven by a validator, live "username available" hints, and anything where the user is meant to see a message form as they type. Fields validated against a server are usually the ones you should leave on the new default, since they are what the change was made for.

## The configuration file

Configuration moves from `formkit.json` to `formkit.config.js`, because computed values are common in real configuration and JSON cannot express them. Run the converter:

```bash
npx formkit migrate-config
```

It handles almost every case, which is not the same as all of them, so read the file it produces before you commit it. The output is an ES module with a default export:

```js
// formkit.config.js
export default {
  locale: 'en',
  theme: 'default',
  apiBase: process.env.FORMKIT_API ?? '/api/forms',
}
```

The last line there is the point of the move: values you previously had to inject at build time or patch after loading can now be computed in the config itself. Delete `formkit.json` once you are satisfied with the conversion, since 3.0 does not read it and leaving it in place invites someone to edit the wrong file.

## `strictValidation` becomes `validation`

The boolean is replaced by a three-way option:

```js
// 2.x
{ strictValidation: true }

// 3.0
{ validation: 'strict' }
```

`true` becomes `'strict'` and `false` becomes `'loose'`. The third value, `'off'`, disables validation entirely and has no equivalent in 2.x, so nothing in your existing configuration should convert to it.

Your old boolean still works in 3.0 and will print a deprecation warning. It is removed in 4.0, so this is a change you can make on your own schedule rather than during the upgrade, as long as you make it before the next major.

## Validators receive a context argument

Validators used to be called with `(value)` and are now called with `(value, context)`, where `context` carries the other field values in the form. Existing one-argument validators keep working exactly as they did, because JavaScript ignores the extra argument.

The new argument is what you need for cross-field rules, which previously had to reach outside the validator for the data:

```js
function matchesPassword(value, context) {
  return value === context.password || 'Passwords do not match'
}
```

## Suggested order

Upgrade Node, install 3.0, and run `npx formkit migrate-config`, reviewing its output. At that point your application should build and run, and the only outstanding work is the timing change: walk your forms, decide which fields need `validateOn: "input"`, and add it. Leave the `strictValidation` rename and any rewrite of validators to use `context` for a later pass, since neither one blocks the upgrade.