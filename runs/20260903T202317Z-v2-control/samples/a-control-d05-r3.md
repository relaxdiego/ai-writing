# Migrating from FormKit 2.x to 3.0

Most of this migration is mechanical, and one command does the bulk of it. There is a single behavioural change that no tool can detect for you: **validators no longer run on every keystroke.** If you read only one section, read [Validation timing](#validation-timing).

## Before you start

FormKit 3.0 requires **Node 18 or later**. Node 16 is no longer supported and is not tested against. Upgrade your runtime before upgrading the package, or the install will fail.

```bash
node --version   # must be >= 18
npm install formkit@3
```

## 1. Move your config to `formkit.config.js`

`formkit.json` is replaced by `formkit.config.js`. The reason is that a lot of configuration turned out to want computed values — environment-dependent endpoints, shared constants, values derived from other values — and JSON has no way to express that.

Run the converter:

```bash
npx formkit migrate-config
```

It reads `formkit.json`, writes `formkit.config.js`, and leaves the original in place so you can diff the two. It handles essentially every configuration we've seen; if it reports something it can't convert, it tells you which key and leaves that key for you to move by hand.

The output is a plain module, so you can now do things like:

```js
// formkit.config.js
const API = process.env.FORMKIT_API ?? "https://api.example.com";

export default {
  endpoint: `${API}/forms`,
  // ...
};
```

Delete `formkit.json` once you've checked the result. FormKit 3.0 does not read it.

## 2. Replace `strictValidation`

The boolean `strictValidation` is now a three-state `validation` option:

| 2.x | 3.0 |
| --- | --- |
| `strictValidation: true` | `validation: "strict"` |
| `strictValidation: false` | `validation: "loose"` |
| — | `validation: "off"` |

`"off"` is new; there was no way to express it in 2.x.

The old boolean still works in 3.0, but logs a deprecation warning on startup. It will be removed in 4.0. `npx formkit migrate-config` performs this rename for you as part of the config conversion, so if you ran step 1 you are likely already done — check for any `strictValidation` set outside the config file.

<a id="validation-timing"></a>
## 3. Validation timing — the one that will break you

**In 2.x, field validators ran on every keystroke. In 3.0, they run when a field loses focus, and on submit.**

Nothing errors, nothing warns, and the migration command cannot detect this. Forms that depended on per-keystroke feedback will simply feel different: the error message that used to appear as the user typed now appears when they tab away.

We changed this because the old behaviour was a real problem for validators that hit the network. A field with a server-side uniqueness check fired one request per character typed — a twelve-character username meant twelve requests, most of them already stale by the time they returned.

To restore the old behaviour for a specific field, set `validateOn`:

```js
{
  name: "coupon",
  validate: isValidCoupon,
  validateOn: "input",   // validate on every keystroke, as in 2.x
}
```

There is no global switch, and that is deliberate: the setting is opt-in per field so that the expensive case has to be chosen explicitly.

**What to do:** go through your fields and decide, for each one, whether immediate feedback was intentional. In practice this is a short list. Good candidates for `validateOn: "input"` are cheap, purely local checks where live feedback is part of the design — password strength meters, character counters, format masks. Anything that makes a request should stay on the new default.

Worth testing by hand rather than trusting your test suite here: tests that call validators directly won't notice the change, because the timing lives in the field, not the validator.

## 4. Validators now receive a context argument

Validator signatures went from `(value)` to `(value, context)`. `context` carries the current values of the other fields, which makes cross-field validation possible without threading state through a closure.

This is additive. **Existing one-argument validators keep working unchanged** — there is nothing to migrate. Adopt the second argument only where you want it:

```js
// still fine
const isPositive = (value) => value > 0 || "Must be positive";

// new: compare against another field
const isAfterStart = (value, context) =>
  value > context.startDate || "End date must be after the start date";
```

## Checklist

- [ ] Node 18 or later installed
- [ ] `npx formkit migrate-config` run, output reviewed, `formkit.json` deleted
- [ ] No remaining `strictValidation` outside the config file
- [ ] Every field audited for whether it relied on per-keystroke validation; `validateOn: "input"` added where it did
- [ ] Forms with network-backed validators tested by hand

Items 1–3 are mechanical and will announce themselves if you get them wrong. Item 4 will not, so give it the time.