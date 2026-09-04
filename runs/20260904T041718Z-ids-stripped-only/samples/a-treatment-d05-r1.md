# Migrating from formkit 2.x to 3.0

One change in this release cannot be automated and will not announce itself at runtime: validators no longer run on every keystroke. In 2.x, a validator fired as the user typed; in 3.0 it fires when the field loses focus, and again on submit. Forms that relied on per-character feedback will look silently less responsive rather than throw an error, so this is the change to audit by hand before you upgrade. The fix is per field: add `validateOn: "input"` to any field that genuinely needs the old timing.

Everything else in 3.0 is either automated by a codemod or backward compatible for the whole 3.x line.

## What changed, and what you have to do

| Change | 2.x | 3.0 | Action |
| --- | --- | --- | --- |
| Config format | `formkit.json` | `formkit.config.js` | Run `npx formkit migrate-config` |
| Validation mode | `strictValidation: boolean` | `validation: "strict" \| "loose" \| "off"` | Optional in 3.0, required by 4.0 |
| Validator signature | `(value)` | `(value, context)` | None; one-argument validators still work |
| Validation timing | Every keystroke | Blur and submit | Manual: add `validateOn: "input"` where needed |
| Node | 16+ | 18+ | Upgrade your runtime and CI images |

## Node 16 is no longer supported

3.0 requires Node 18 or later. Bump the runtime in your local environment, your CI images, and any deployment target before you install, since an install on Node 16 will fail rather than degrade. If your CI matrix still lists 16, drop that entry in the same commit as the upgrade so a red build points at the version you removed rather than at formkit.

## The configuration file becomes JavaScript

`formkit.json` is replaced by `formkit.config.js`. The reason is that configuration frequently needs computed values, and JSON has no way to express them: environment variables, values shared with another part of the build, or a list assembled from a directory. A JSON file can only restate constants, so anyone in that position was generating the file from a script and checking the output into the repository.

Run the codemod from the root of your project:

```
npx formkit migrate-config
```

It reads `formkit.json`, writes an equivalent `formkit.config.js`, and it is expected to handle almost every configuration in the wild. Review the generated file and commit both the new file and the deletion of the old one together. The new file is a module that exports the configuration object, so anything you were previously generating with a build step can now be computed in place:

```js
export default {
  theme: process.env.FORMKIT_THEME ?? "default",
  locales: ["en", "fr"],
};
```

If the codemod reports something it could not convert, that entry is the one to translate by hand; the rest of the file is still written out around it.

## `strictValidation` becomes `validation`

The boolean is replaced by a three-valued option, because two states were not enough to describe what people wanted. `strictValidation: true` becomes `validation: "strict"`, and `strictValidation: false` becomes `validation: "loose"`. The third value, `"off"`, disables validation entirely and has no equivalent in 2.x, so no migration produces it; reach for it only where you want validation genuinely gone rather than permissive.

The old boolean still works in 3.0. It prints a deprecation warning on startup and will be removed in 4.0, which gives you the whole 3.x line to make the change. Since it is a mechanical rename in a single file, the pragmatic move is to do it while you have the config open for the codemod rather than to carry the warning forward.

## Validators receive a second argument

Field validators are now called as `(value, context)`, where `context` carries the values of the other fields in the form. This makes cross-field rules possible without reaching outside the validator for form state:

```js
function confirmPassword(value, context) {
  return value === context.password || "Passwords do not match";
}
```

Nothing is required of you here. Existing one-argument validators keep working unchanged, because a function that ignores its second parameter behaves exactly as it did before. Adopt the argument where a rule needs it and leave the rest alone.

## Validators run on blur and submit, not on every keystroke

This is the change that requires you to look at your forms. In 2.x every keystroke ran the field's validators. That behaviour is fine for a local regular expression check and badly wrong for anything that talks to a server: a form that verified a username against an API sent one request per character typed, so a twelve-character username produced twelve requests, of which eleven were answering a question nobody had finished asking. 3.0 validates when a field loses focus and again on submit, which collapses that to one request per completed entry.

Where per-keystroke feedback is the point rather than an accident, ask for it explicitly on the field:

```js
{
  name: "coupon",
  validateOn: "input",
  validate: checkCouponFormat,
}
```

Two categories deserve the setting and most fields do not. A validator that runs entirely in the browser and gives progressive feedback as the user types is the honest case: a password strength meter, a character counter, a format mask. A validator that performs a network request, a database lookup, or any other expensive check is the case the new default exists to protect, and moving it back to `"input"` restores the request-per-character behaviour along with the responsiveness.

To audit an existing project, list every field that has a validator attached and decide for each one whether a user would notice the difference between feedback while typing and feedback on leaving the field. Fields validated against a server almost never need it; fields whose whole purpose is live feedback almost always do. Because nothing warns you about this at runtime, a form that is missed will simply feel different rather than break, which is why the pass is worth doing deliberately rather than waiting for a bug report.

## A suggested order

Upgrade Node first, so that the remaining steps run on the runtime you are shipping. Run `npx formkit migrate-config` next and review its output, renaming `strictValidation` to `validation` in the same pass while the file is in front of you. Install 3.0 and confirm the application starts with no deprecation warnings. Then walk the list of validated fields and add `validateOn: "input"` where the old timing was load-bearing, which is the only step that needs judgement rather than a command.