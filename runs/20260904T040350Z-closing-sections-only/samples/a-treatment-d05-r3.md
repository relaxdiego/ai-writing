# Migrating from formkit 2.x to 3.0

One change in this release can break a working form with no error and no warning: validators no longer run on every keystroke. Everything else is either converted for you by a codemod or keeps working untouched, so the section on validation timing is the one to read slowly.

## What changed

| Change | What you do | Breaks if you ignore it |
| --- | --- | --- |
| Node 16 support dropped | Move to Node 18 or later | Yes, at install or build |
| `formkit.json` → `formkit.config.js` | Run `npx formkit migrate-config` | Yes, your config stops being read |
| `strictValidation` → `validation` | Codemod handles it, or edit by hand | Not yet; warns in 3.0, removed in 4.0 |
| Validators receive `(value, context)` | Nothing | No |
| Validators run on blur and submit, not per keystroke | Add `validateOn: "input"` to affected fields | Yes, and silently |

## Node 18 or later

Do this before anything else, since the codemod and your build both run on it. Update the Node version in your CI configuration, your Dockerfile, and the `engines` field of your `package.json`. Node 16 has been out of support since September 2023, so in most projects this is a version bump in a config file rather than a code change.

## The configuration file

`formkit.json` becomes `formkit.config.js`. The reason is that a JSON file cannot compute anything, and people were maintaining several near-identical config files, or generating one at build time, to work around it.

Run the codemod from the root of your project:

```
npx formkit migrate-config
```

It reads `formkit.json`, writes `formkit.config.js` beside it, and is expected to handle almost every configuration it finds. Read the file it produces before you commit it. Once you are satisfied, delete `formkit.json`: 3.0 does not read it, so a leftover copy is harmless to the build but will mislead the next person who edits it.

The point of the move is what you can now write:

```js
// formkit.config.js
export default {
  apiBase: process.env.FORMKIT_API ?? 'https://api.example.com',
  validation: process.env.NODE_ENV === 'production' ? 'strict' : 'loose',
}
```

## strictValidation becomes validation

The boolean is replaced by a three-value string, because there was previously no way to say that validation should not run at all.

- `strictValidation: true` becomes `validation: "strict"`
- `strictValidation: false` becomes `validation: "loose"`
- `validation: "off"` is new and has no 2.x equivalent

The codemod applies the first two translations. If you are editing by hand, note that `false` meant loose validation rather than no validation, so translate it to `"loose"` and reach for `"off"` only where you actively want validation switched off.

The old boolean still works in 3.0. It prints a deprecation warning on startup and will be removed in 4.0, so this is a change you can schedule rather than one you have to make today.

## Validators receive a context argument

A field validator used to be called with `(value)` and is now called with `(value, context)`, where `context` carries the values of the other fields in the form. Existing one-argument validators are unaffected: they simply ignore the second argument.

The new argument is there for cross-field rules that previously needed a closure over form state:

```js
const matchesPassword = (value, context) =>
  value === context.values.password || 'Passwords do not match'
```

## Validators no longer run on every keystroke

This is the change with no automatic fix, and the one that can leave a form looking fine while behaving differently.

In 2.x, a field's validators ran on every keystroke. In 3.0 they run when the field loses focus, and again on submit. The change was made because a validator that calls a server, checking whether a username is taken for instance, was firing one request per character typed.

Nothing warns you about this. A field that showed an error as the user typed will now show the same error only after they tab away, and only a person looking at the form will notice.

To restore the old behaviour on a field, set `validateOn`:

```js
{
  name: 'username',
  validateOn: 'input',
  validators: [isAvailable],
}
```

Fields that should keep per-keystroke validation are the ones where the message is feedback the user acts on while typing: password strength meters, character budgets, format hints on a phone number or a postcode. Fields that check something on the server are the ones the new default was written for; leave those alone.

Two things help you find the affected fields, since there is no way to detect them automatically. Search for validators that are wrapped in a debounce, because a debounce is the workaround somebody wrote when per-keystroke validation cost too much, and those fields are exactly the ones that wanted `validateOn: "input"` all along. You can often drop the debounce at the same time. Then check your test suite: a test that types into a field and immediately asserts that an error appeared will now fail, and each failure points at a field whose timing changed. Those failures are informative rather than a nuisance, so read them before you adjust them.

## Upgrade checklist

1. Move to Node 18 or later, in CI and in local development.
2. Run `npx formkit migrate-config`, review `formkit.config.js`, delete `formkit.json`.
3. Confirm the deprecation warning for `strictValidation` is gone, or note it as work due before 4.0.
4. Add `validateOn: "input"` to fields whose validation the user reads while typing.
5. Run the form tests and treat each timing failure as a field to decide about.

One detail I filled in: the guide reads the other fields as `context.values.password`. If the released API exposes them under a different accessor, that example is the only place to correct.