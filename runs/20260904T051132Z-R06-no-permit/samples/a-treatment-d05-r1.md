# Migrating to formkit 3.0

formkit 3.0 requires Node 18 or later. Node 16 is no longer supported, so check your CI images and deployment targets before you start — an install on Node 16 will fail rather than degrade.

Most of this migration is mechanical, and one part of it is not. The table below is the whole surface:

| Change | 2.x still works? | Fix |
| --- | --- | --- |
| `formkit.json` → `formkit.config.js` | No | `npx formkit migrate-config` |
| `strictValidation` → `validation` | Yes, with a warning; removed in 4.0 | Rename by hand, or let `migrate-config` do it |
| Validators receive `(value, context)` | Yes, unchanged | Nothing required |
| Validators run on blur and submit, not per keystroke | No | Set `validateOn: "input"` per field — **no automatic fix** |
| Node 16 | No | Upgrade to 18+ |

## Validation timing: the change that needs your attention

In 2.x, a field's validators ran on every keystroke. In 3.0 they run when the field loses focus, and again on submit. Nothing warns you about this, and nothing in your code changes: the validators still run, still receive the same value, and still return the same result. They just run later. If your users relied on seeing an error appear as they typed, they will now see it when they tab away.

We changed this because the old behaviour was actively harmful for validators that make a network call. A username-availability check written the obvious way sent one request per character typed, and the only way to avoid it was to debounce inside every such validator.

To restore the old behaviour for a field, set `validateOn: "input"` on that field:

```js
{
  name: "password",
  validators: [minLength(12), hasNumber],
  validateOn: "input",
}
```

There is no global switch, and this is deliberate: the fields where per-keystroke validation is worth having are usually a small subset, and the fields where it is expensive are exactly the ones a global switch would re-break.

Go through your forms and look for fields whose validation is meant to be read while typing — password strength requirements, character or word limits, format hints on phone numbers and card numbers, anything that pairs with a live indicator in the UI. Those want `validateOn: "input"`. Fields that validate by calling your server should be left alone; they are the reason for the change. Everything else — required fields, email format, matching confirmation fields — is generally better on blur, and you can leave it at the new default.

## Configuration moves to `formkit.config.js`

`formkit.json` is replaced by `formkit.config.js`, so that options can be computed rather than written out as literals. Run the converter from your project root:

```
npx formkit migrate-config
```

It reads `formkit.json`, writes `formkit.config.js`, and leaves the old file in place for you to delete once you are satisfied with the result. It handles essentially every configuration we have seen, including the `strictValidation` rename described below. Read the generated file before committing it, then remove `formkit.json`; if both files are present, 3.0 uses the `.js` one and ignores the JSON.

The new file exports an object, which means values that used to be duplicated or hard-coded can now come from the environment or from shared modules:

```js
export default {
  validation: process.env.NODE_ENV === "production" ? "strict" : "loose",
  locale: await resolveLocale(),
};
```

## `strictValidation` becomes `validation`

The boolean is replaced by a three-value option:

```js
// 2.x
{ strictValidation: true }
{ strictValidation: false }

// 3.0
{ validation: "strict" }
{ validation: "loose" }
```

`true` maps to `"strict"` and `false` maps to `"loose"`. The old boolean is still honoured in 3.0 and prints a deprecation warning; it will be removed in 4.0, so treat the warning as work to do rather than noise to filter. The third value, `"off"`, disables validation entirely and has no 2.x equivalent — it is new capability, not a renaming of anything you had.

## Validators receive a second argument

Validators are now called as `(value, context)`, where `context` holds the other field values in the form. A validator you wrote for 2.x takes one argument, ignores the second, and keeps working exactly as it did — there is nothing to migrate here.

The argument is there so that cross-field rules stop needing a closure over form state:

```js
const matchesPassword = (value, context) =>
  value === context.password || "Passwords do not match";
```

## Suggested order

Upgrade Node first, since nothing else can be tested until the install succeeds. Then run `migrate-config`, review the generated file, and delete `formkit.json`. At that point your application should run, and any remaining `strictValidation` warnings tell you what the converter did not reach. Do the field-by-field pass for `validateOn: "input"` last, with the application running, because that is the change you have to verify by looking at forms rather than by reading a log.