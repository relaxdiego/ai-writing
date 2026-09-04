# Migrating from formkit 2.x to 3.0

One change in this release alters behaviour without touching your code: validators no longer run on every keystroke. They now run when a field loses focus and on submit. Nothing warns you about this, and no tool can fix it, because whether per-keystroke validation was load-bearing for a given field is a judgement only you can make. Read [Validation timing](#validation-timing-changed) first and audit your fields against it. The rest of the release is mechanical, and most of it is either automated or backwards compatible.

## Summary

| Change | What you have to do | When 2.x code stops working |
| --- | --- | --- |
| Node 16 dropped | Upgrade to Node 18 or later | Immediately, at install |
| Validation runs on blur and submit | Audit fields; add `validateOn: "input"` where needed | Immediately, silently |
| `formkit.json` becomes `formkit.config.js` | Run `npx formkit migrate-config` | Immediately |
| `strictValidation` becomes `validation` | Rename at your convenience | 4.0 |
| Validators receive `(value, context)` | Nothing | Not planned |

## Node 18 is now the minimum

Node 16 is no longer supported. Upgrade your local toolchain, your CI images and your deployment targets to Node 18 or later before you install 3.0, since an install on Node 16 will fail rather than degrade.

## Validation timing changed

In 2.x, every validator on a field ran on each keystroke. In 3.0 a field validates when it loses focus, and every field validates on submit. The old behaviour was expensive for anyone whose validators talked to a server: a username field checking availability against an API fired one request per character typed, which is the cost this change removes.

Most fields are better off with the new default, and you can leave them alone. The fields to look for are the ones where the user expects feedback while typing rather than after moving away: password strength meters, character counters, live format hints on phone numbers or card numbers, and anything whose validator drives visible state other than an error message. For each of those, restore the old behaviour on that field alone:

```js
{
  name: "password",
  validators: [strength],
  validateOn: "input",
}
```

There is no global switch that returns the whole form to 2.x timing, and that is deliberate. Setting `validateOn: "input"` on every field would reintroduce the per-character request problem on exactly the fields the change was made to protect.

## The configuration file moves

`formkit.json` is replaced by `formkit.config.js`, which exports the same configuration as a JavaScript object. The reason is that JSON could not compute anything, so values that depended on the environment, on a shared constant, or on any arithmetic had to be duplicated or injected by a build step.

Run the converter from your project root:

```
npx formkit migrate-config
```

It reads `formkit.json`, writes `formkit.config.js` and leaves the original in place so you can compare the two. It handles almost every configuration, but read the output before deleting the old file, and check anything unusual in your configuration survived the trip. Once you are satisfied, remove `formkit.json`; if both files are present, 3.0 uses `formkit.config.js` and ignores the JSON.

The new file is ordinary JavaScript, so the values that forced you into a build step can now be written directly:

```js
export default {
  endpoint: process.env.FORMKIT_ENDPOINT,
  timeout: 30 * 1000,
  validation: "strict",
}
```

## `strictValidation` becomes `validation`

The boolean `strictValidation` is replaced by `validation`, which takes `"strict"`, `"loose"` or `"off"`. Translate `true` to `"strict"` and `false` to `"loose"`:

```js
// 2.x
strictValidation: true

// 3.0
validation: "strict"
```

The third value has no 2.x equivalent. `"off"` disables validation entirely, which is useful for a form whose checking happens server-side, and it is not what `false` meant.

The old key still works in 3.0 and prints a deprecation warning on startup. It will be removed in 4.0, so this is a rename you can schedule rather than one that blocks the upgrade. If you ran `npx formkit migrate-config`, the conversion has already been done for you in the generated file.

## Validators receive a second argument

Field validators are now called as `(value, context)`, where `context` carries the values of the other fields in the form. Validators written against the one-argument signature continue to work unchanged, and there is no plan to remove that form, so this is available to you rather than required of you.

The argument exists for validators that could not previously be expressed without reaching outside the form:

```js
function matchesPassword(value, context) {
  return value === context.password || "Passwords do not match"
}
```