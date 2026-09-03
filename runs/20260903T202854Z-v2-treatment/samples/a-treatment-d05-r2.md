# Migrating from formkit 2.x to 3.0

One change in 3.0 alters your forms' behaviour without raising an error or printing a warning: validators no longer run on every keystroke. They now run when a field loses focus, and on submit. Nothing in your code breaks and nothing appears in the console, so a form that showed an error as the user typed will simply stay quiet until they tab away. If any of your fields depend on per-keystroke feedback, you have to opt them back in by hand, because no tool can tell which ones those are.

Everything else in this release is either automated or backward compatible for the whole 3.x line.

## Order of work

1. Move to Node 18 or later.
2. Run `npx formkit migrate-config` and review the result.
3. Audit your fields for the validation-timing change and add `validateOn: "input"` where you need it.
4. Optionally, rename `strictValidation` and adopt the second validator argument.

Steps 1 to 3 are required. Step 4 can wait, though not past 4.0 for the rename.

## Node 16 is no longer supported

3.0 requires Node 18 or later. Upgrade your local toolchain, your CI images and your deployment runtime before installing, or the install itself will fail.

## The configuration file moves

`formkit.json` is replaced by `formkit.config.js`. The reason is that people kept needing to compute configuration values, read an environment variable, derive a URL, branch on the build target, and JSON gives you nowhere to put that logic.

Run the converter from your project root:

```
npx formkit migrate-config
```

It reads `formkit.json`, writes `formkit.config.js` and leaves the original in place so you can compare the two. It is expected to handle almost every configuration, but read the output before you delete the old file, and pay particular attention to anything that was encoded as a string because JSON had no better type for it.

The new file is a module, so a value you previously had to hard-code can now be computed:

```js
export default {
  apiBase: process.env.FORMKIT_API ?? "https://api.example.com",
  locale: process.env.LANG?.slice(0, 2) ?? "en",
}
```

## `strictValidation` becomes `validation`

The boolean is replaced by a three-valued string option. `strictValidation: true` becomes `validation: "strict"`, and `strictValidation: false` becomes `validation: "loose"`. The third value, `validation: "off"`, disables validation entirely and has no equivalent in 2.x.

The old boolean still works in 3.0 and prints a deprecation warning; it is removed in 4.0. Since the mapping is exact, this is a safe find-and-replace whenever you get to it.

## Validators receive a second argument

A field validator used to be called with `(value)` and is now called with `(value, context)`, where `context` carries the values of the other fields in the form. This makes cross-field rules, a confirmation field or a date range, possible without reaching outside the validator.

```js
// 2.x, still valid in 3.0
const notEmpty = (value) => value.trim().length > 0

// 3.0
const matchesPassword = (value, context) =>
  value === context.password || "Passwords do not match"
```

JavaScript ignores extra arguments, so every one-argument validator you already have keeps working unchanged. There is nothing to migrate here; the second argument is available when you want it.

## When validators run

In 2.x a validator ran on every keystroke. In 3.0 it runs when the field loses focus, and again on submit. The old behaviour meant that any validator making a server-side check, a username-availability lookup being the usual case, fired one request per character typed.

To restore per-keystroke validation, set `validateOn` on the individual field:

```js
{
  name: "coupon",
  validators: [isValidCoupon],
  validateOn: "input",
}
```

The option is per field, which is deliberate: the fields that genuinely benefit from immediate feedback are usually a small subset, and the ones that were driving the request storms are usually not among them.

Two things are worth checking while you are in there. First, any debouncing or throttling you added to work around the old behaviour is now redundant on fields you leave at the default, and keeping it will delay the blur-triggered validation for no benefit. Second, tests that type into a field and then assert on an error message will now fail, because the error no longer exists until focus leaves the field; those tests need a blur, not a rewrite.