# Migrating from formkit 2.x to 3.0

Most of this migration is automated. One change is not, and it changes behaviour silently: **validators no longer run on every keystroke.** Nothing errors, nothing warns — validation just happens later than it used to. If you read only one section, read [Step 3](#step-3-decide-where-you-need-per-keystroke-validation).

## At a glance

| Change | What you do |
|---|---|
| Node 16 dropped, 18+ required | Upgrade your runtime first |
| `formkit.json` → `formkit.config.js` | Run `npx formkit migrate-config` |
| Validation runs on blur/submit, not on input | Manual — audit your fields |
| `strictValidation` → `validation` | Rename; old form works until 4.0 |
| Validators receive `(value, context)` | Nothing; existing validators keep working |

---

## Step 1: Move to Node 18 or later

Node 16 is no longer supported. Do this before anything else — the 3.0 package won't install on 16.

```bash
node --version   # must be >= 18
```

Update your CI images, Dockerfiles, and any `engines` field at the same time. It's easy to upgrade locally and then discover the pipeline is still on 16.

## Step 2: Convert your config file

Configuration moves from `formkit.json` to `formkit.config.js`. The reason is that people kept needing to compute configuration values — environment-dependent endpoints, values derived from other values — and JSON can't do that.

```bash
npx formkit migrate-config
```

This handles almost every case, but read the result before you commit it. Then delete `formkit.json` and check that nothing else still references it (build scripts and Docker `COPY` lines are the usual stragglers).

Before, `formkit.json`:

```json
{
  "locale": "en-US",
  "endpoint": "https://api.example.com/forms"
}
```

After, `formkit.config.js`:

```js
export default {
  locale: 'en-US',
  endpoint: 'https://api.example.com/forms',
}
```

Now that it's a module, you can compute values — which was the point of the change:

```js
export default {
  locale: process.env.LOCALE ?? 'en-US',
  endpoint: process.env.FORMS_ENDPOINT ?? 'https://api.example.com/forms',
}
```

## Step 3: Decide where you need per-keystroke validation

**This is the breaking change with no automatic fix.**

In 2.x, validators ran on every keystroke. In 3.0 they run when a field loses focus, and on submit.

The old behaviour meant a form with a server-side check fired one request per character typed. The new default is what almost everyone wanted. But if you had a field whose whole job was instant feedback, it now feels broken — the message appears a beat later than the user expects.

Opt back in per field:

```js
{
  name: 'password',
  validate: passwordStrength,
  validateOn: 'input',   // restores 2.x timing for this field only
}
```

There's no codemod for this, because whether a field wants instant feedback is a design decision, not a mechanical one. Go through your validated fields and ask: *does the user need to see this while they type?*

- **Yes** — password strength meters, character counters, live format hints as you type. Add `validateOn: "input"`.
- **No** — everything else. Leave it alone; blur-and-submit is the better behaviour, and for anything hitting a server it's the whole reason for the change.

If you're not sure, ship the default. It's easy to add `validateOn: "input"` to one field later after someone notices; it's harder to notice you've quietly restored a request-per-character.

**Watch your test suite.** Tests that type one character and immediately assert on an error message will now fail. That's the change working correctly, not a regression — add a blur or a submit before the assertion.

## Step 4: Rename `strictValidation`

`strictValidation` becomes `validation`, which takes a string instead of a boolean:

| 2.x | 3.0 |
|---|---|
| `strictValidation: true` | `validation: "strict"` |
| `strictValidation: false` | `validation: "loose"` |
| — | `validation: "off"` |

`"off"` is new; there was no way to express it in 2.x.

The boolean still works in 3.0 and prints a deprecation warning. **It is removed in 4.0**, so do the rename now rather than filing it away. If `migrate-config` didn't already rewrite it, it's a one-line change:

```js
export default {
  validation: 'strict',
}
```

## Step 5: Nothing — validator context

Field validators used to receive `(value)`. They now receive `(value, context)`, where `context` carries the other field values.

This is purely additive. Your existing one-argument validators keep working, unchanged, forever — a function that ignores its second argument is still a valid function. There is no migration step here.

It does mean cross-field validation no longer needs a workaround:

```js
// 2.x — reach outside the validator for the other value
const confirmPassword = (value) => value === form.getValue('password')

// 3.0 — it's just there
const confirmPassword = (value, context) => value === context.password
```

Adopt it when you touch those validators. There's no deadline.

---

## Migration checklist

- [ ] Runtime on Node 18+, including CI and containers
- [ ] `npx formkit migrate-config` run, output reviewed, `formkit.json` deleted
- [ ] No remaining references to `formkit.json` in build scripts
- [ ] `strictValidation` renamed to `validation` (no deprecation warnings in the log)
- [ ] Every validated field reviewed for whether it needs `validateOn: "input"`
- [ ] Tests that assert on validation errors updated to blur or submit first
- [ ] Manual pass over your highest-traffic form, watching the network tab

That last item is worth the five minutes. The validation-timing change is the one that produces no error message, so a human looking at a real form is the only reliable detector.