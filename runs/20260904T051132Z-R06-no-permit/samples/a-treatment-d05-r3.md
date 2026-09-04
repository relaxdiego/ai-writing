# Migrating from formkit 2.x to 3.0

One change in 3.0 needs you to look at your forms by hand: validators no longer run on every keystroke. They run when a field loses focus and on submit. Nothing throws and nothing warns when this affects you, so a form that relied on per-keystroke feedback will simply feel different, and you will only notice it by using the form or by auditing your fields. Everything else in this release is either converted by a command or keeps working as it did in 2.x.

| Change | Automatic | What you do |
| --- | --- | --- |
| Validators run on blur and submit, not per keystroke | No | Audit fields; add `validateOn: "input"` where live feedback matters |
| `formkit.json` → `formkit.config.js` | Yes | Run `npx formkit migrate-config`, review the result |
| `strictValidation` → `validation` | Deprecated, still works | Rename before 4.0 |
| Validators receive `(value, context)` | Yes, backward compatible | Nothing; opt in when you need cross-field access |
| Node 16 dropped | No | Move to Node 18 or later |

## Upgrade sequence

1. Move your runtime and CI images to Node 18 or later. 3.0 will not install or run on Node 16, so doing this first keeps the rest of the migration from failing for an unrelated reason.
2. Install 3.0 and run `npx formkit migrate-config` in the directory holding `formkit.json`.
3. Read the generated `formkit.config.js` and diff it against the old file. The converter is expected to handle almost every configuration, but "almost every" is not "every", and a config that used unusual nesting or non-standard keys is where it is most likely to need a hand.
4. Rename `strictValidation` if the converted file still carries it.
5. Audit your fields for per-keystroke validation, which is the part of this migration no tool can do for you.

## The configuration file

`formkit.json` becomes `formkit.config.js`. The reason is that people kept needing to compute configuration values, reading an environment variable or deriving one setting from another, and JSON has no way to express that. The new file is a module with a default export, so anything you can compute in JavaScript is now available to you.

The converter produces a direct translation. A file like this:

```json
{
  "strictValidation": true,
  "locale": "en"
}
```

comes out as this:

```js
export default {
  strictValidation: true,
  locale: "en",
}
```

Once the file is JavaScript you can start using that fact, which is the point of the change:

```js
export default {
  validation: process.env.NODE_ENV === "production" ? "strict" : "loose",
  locale: "en",
}
```

## `strictValidation` becomes `validation`

The boolean is replaced by a three-value option, `validation: "strict" | "loose" | "off"`. Your old boolean still works in 3.0 and prints a deprecation warning at startup; it is removed in 4.0, so treat the warning as a task rather than as noise. The mapping is direct: `true` becomes `"strict"` and `false` becomes `"loose"`. The third value, `"off"`, has no 2.x equivalent, so no automatic conversion will ever produce it. Set it yourself if you want validation disabled outright rather than merely relaxed.

## Validators receive a second argument

A validator used to be called with `(value)` and is now called with `(value, context)`, where `context` carries the other field values in the form. This is purely additive. JavaScript ignores extra arguments, so every one-argument validator you have written keeps working unchanged, and there is no deprecation attached to writing them that way.

The second argument is there for validation that depends on another field, which previously had no clean way to reach it:

```js
// 2.x style, still correct in 3.0
const required = (value) => value.length > 0 || "Required"

// 3.0, reading a sibling field
const matchesPassword = (value, context) =>
  value === context.password || "Passwords do not match"
```

## When validators run

This is the breaking change, and it has no automatic fix.

In 2.x, a field's validators ran on every keystroke. In 3.0 they run when the field loses focus, and again on submit. The old behaviour meant that any validator making a server-side check fired one request per character typed, so a user typing an eight-character username generated eight requests, and the responses could arrive out of order. Deferring to blur makes that one request for one completed value.

The cost is that validation which was genuinely useful per keystroke also stops being per keystroke. Password strength feedback, a live character counter, and a confirmation field that should turn green the moment it matches all become blur-time in 3.0 unless you say otherwise. Restore the old timing on a single field with `validateOn`:

```js
{
  name: "passwordConfirm",
  validateOn: "input",
  validators: [matchesPassword],
}
```

To find what is affected, go through your fields and ask, for each one, whether a user is expected to see the validation result while still typing in that field. Fields whose validators touch the network are the ones to leave alone: they are the reason the default changed, and they will get faster and quieter for free. Fields validating locally against something the browser already knows are the candidates for `validateOn: "input"`.