# Migrating from formkit 2.x to 3.0

One change in 3.0 breaks working code without telling you: validators no longer run on every keystroke. They run when a field loses focus and on submit. Nothing throws, nothing warns, and forms that gave live feedback as the user typed will simply stop doing so until you opt those fields back in. Everything else in this release either migrates automatically or keeps working with a deprecation warning.

## Upgrade order

1. Move to Node 18 or later. Node 16 is no longer supported, so nothing else here matters until this is done.
2. Install 3.0 and run `npx formkit migrate-config`.
3. Find the fields that depended on per-keystroke validation and add `validateOn: "input"` to each.
4. Rename `strictValidation` when convenient, before 4.0.

## Node 16 is no longer supported

3.0 requires Node 18 or later. If your CI images or deploy targets still run 16, upgrade them first: an install on 16 is not a supported configuration, and problems you hit there are not worth debugging against the rest of this list.

## The configuration file becomes JavaScript

`formkit.json` is replaced by `formkit.config.js`. JSON could not express a computed value, which meant configuration that depended on an environment variable, a build flag, or anything derived had to be generated or worked around outside of formkit. The config is now a JavaScript module, so those values can just be computed in place.

Run the converter from your project root:

```
npx formkit migrate-config
```

It reads the existing `formkit.json` and writes `formkit.config.js`, and it is expected to handle almost every case. Commit your work before running it so the diff is easy to read, then check the generated file: this is the moment to replace anything you were previously hard-coding or generating with a real expression.

## `strictValidation` becomes `validation`

The boolean is replaced by a three-way option. Your existing configuration still works in 3.0 and will print a deprecation warning; the boolean is removed in 4.0.

| 2.x | 3.0 | Behaviour |
| --- | --- | --- |
| `strictValidation: true` | `validation: "strict"` | Unchanged |
| `strictValidation: false` | `validation: "loose"` | Unchanged |
| no equivalent | `validation: "off"` | New: validation does not run |

`"off"` had no expression in 2.x, so no existing configuration maps onto it. Reach for it only where you genuinely want validation disabled rather than relaxed.

## Validators receive a second argument

A field validator used to be called with `(value)` and is now called with `(value, context)`, where `context` carries the values of the other fields on the form. This is additive. Your one-argument validators keep working unchanged, and there is nothing to migrate. The argument exists so that a validator that needs to compare against a sibling field, such as a confirmation or a date range, can read it directly instead of reaching outside the form for it.

## Validators no longer run on every keystroke

This is the change with no automatic fix.

In 2.x a validator ran on each input event. A validator that called a server therefore issued one request per character typed, which is the behaviour this release exists to stop. In 3.0 validation runs when a field loses focus, and on submit.

Where you want the old behaviour, set it on the field:

```js
{
  name: "username",
  validateOn: "input",
}
```

The fields worth reviewing are the ones where the timing was the point: a username or coupon code that showed availability as the user typed, a password strength meter, a character counter driven by a validator, or anything whose error message was meant to appear and disappear mid-word. Grep alone will not find these, because the calling code did not change. The reliable pass is to open each form and ask whether a user was ever meant to see a validation result before leaving the field.

Before you add `validateOn: "input"` to a field that talks to a server, note that you are restoring the per-character request pattern along with the live feedback. If the field needs both, debounce inside the validator or check availability at blur and keep only the cheap format check on input.