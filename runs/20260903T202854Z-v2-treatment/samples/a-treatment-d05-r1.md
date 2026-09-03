# Migrating from formkit 2.x to 3.0

One change in this release alters behaviour silently: validators no longer run on every keystroke. They now run when a field loses focus, and on submit. No warning is printed, no codemod detects it, and a form that gave feedback as the user typed under 2.x will stop doing so until you opt back in field by field with `validateOn: "input"`. Read the last section before you ship, even if the rest of the migration goes cleanly.

Everything else here is either converted for you by a command or kept working for the whole 3.x line.

## Node 18 or later

Node 16 support is dropped. Check your version with `node --version` and upgrade your CI images and deployment targets before anything else, since the migration command below runs through the formkit CLI and will not start on 16.

## The configuration file moves to formkit.config.js

`formkit.json` is replaced by `formkit.config.js`. The reason is that people needed to compute configuration values — read an environment variable, derive a URL, share a constant with the rest of the application — and JSON has no way to express that.

Run:

```
npx formkit migrate-config
```

It reads your existing `formkit.json`, writes `formkit.config.js` beside it, and handles almost every configuration we have seen. Review the result, commit it, and delete `formkit.json`.

If your configuration uses something the command cannot translate, the manual conversion is mechanical: the JSON object becomes the default export of a JavaScript module.

```js
// formkit.config.js
export default {
  theme: "default",
  locale: "en",
  apiUrl: process.env.FORMKIT_API_URL,  // now possible
}
```

## strictValidation becomes validation

The boolean `strictValidation` is replaced by `validation`, which takes `"strict"`, `"loose"` or `"off"`. Where you had `strictValidation: true`, write `validation: "strict"`; where you had `false`, write `validation: "loose"`. The third value is new, and turns validation off entirely — there was no way to express that in 2.x.

The old boolean still works in 3.0, but every run prints a deprecation warning, and it is removed in 4.0. `migrate-config` performs this rename in your configuration file; if you also set the option in code, change it there by hand.

## Validators receive a context argument

Field validators used to be called with `(value)` and are now called with `(value, context)`, where `context` carries the values of the other fields in the form. This is additive. Every existing one-argument validator keeps working unchanged, and there is nothing to migrate unless you want the new argument.

```js
// still valid
const required = (value) => value.length > 0

// new: cross-field validation without reaching outside the validator
const confirmPassword = (value, context) => value === context.password
```

## Validation now runs on blur, not on input

This is the change that needs your attention, because nothing detects it for you.

In 2.x, every validator ran on each keystroke. That made forms with server-side checks fire one request per character typed, which is the behaviour we set out to fix. In 3.0, validators run when a field loses focus and again on submit.

To restore per-keystroke validation for a field, set `validateOn: "input"` on that field:

```js
{
  name: "coupon",
  validators: [validCouponFormat],
  validateOn: "input",
}
```

Go through your forms and identify the fields where the user was meant to see feedback while typing. In practice these are the live-feedback cases: password strength meters, character counters, format hints on a phone number or postcode. Fields that simply report "this is required" or "that is not a valid email" are usually better on blur, which is why the default changed, so treat each one as a decision rather than restoring `"input"` everywhere.

Take particular care with any validator you re-enable on `"input"` that calls a server. That combination reproduces the request-per-character problem exactly, so debounce the call inside the validator before you turn it back on.

## Order of work

1. Upgrade to Node 18 or later, including CI and deployment.
2. Run `npx formkit migrate-config`, review the generated `formkit.config.js`, delete `formkit.json`.
3. Replace any remaining `strictValidation` in application code with `validation`.
4. Audit each form for fields that need `validateOn: "input"`, and debounce any server-backed validator among them.

Steps 1 to 3 are mechanical and will tell you when they are wrong. Step 4 will not, so it is the one worth a pass through the forms with a browser open.