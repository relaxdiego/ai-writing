# Migrating from formkit 2.x to 3.0

Most of this release migrates automatically. There is **one change that will alter your app's behaviour without any error or warning** — the validation timing change in Step 3. Read that section even if you skip the rest.

## Summary

| Change | Action needed |
|---|---|
| Node 16 dropped, 18+ required | Upgrade Node |
| `formkit.json` → `formkit.config.js` | Run one command |
| Validators run on blur/submit, not per keystroke | **Manual review — no automatic fix** |
| `strictValidation` → `validation` | Optional now, required before 4.0 |
| Validators receive `(value, context)` | None |

## Step 1: Node 18 or later

formkit 3.0 drops Node 16. Check your version, your CI images, and your deployment runtime:

```
node --version
```

If you're on 16, upgrade before installing 3.0.

## Step 2: Move your configuration file

Configuration moves from `formkit.json` to `formkit.config.js`. The reason is that people were routinely hitting the wall of JSON not being able to compute anything — reading an environment variable, deriving one option from another, sharing a constant with the rest of the app. A JS module can do all of that.

Run the codemod from your project root:

```
npx formkit migrate-config
```

It reads `formkit.json` and writes `formkit.config.js`.

This handles almost every configuration, but "almost" is doing real work in that sentence — read the generated file before you commit it. Two things to confirm: that every key from your old file made it across, and that the values that were strings in JSON are still the types you expect. If something didn't convert, it will be an unusual option rather than a common one, and you can port it by hand.

Now that the file is JavaScript, the things you were working around in 2.x become ordinary code:

```js
// formkit.config.js
export default {
  apiUrl: process.env.FORMKIT_API_URL,
  timeout: process.env.CI ? 30_000 : 5_000,
}
```

## Step 3: Validators now run on blur and submit

**This is the breaking change with no automatic fix.**

In 2.x, field validators ran on every keystroke. In 3.0 they run when a field loses focus, and again on submit.

This changed because per-keystroke validation was pathological for any validator that talked to a server: typing an eight-character username fired eight requests, seven of which were about a value the user was still in the middle of typing. Blur-based validation fires one.

Nothing errors when you upgrade. Forms keep working. What changes is *when* the user sees the message — after they leave the field rather than as they type.

### Deciding which fields to change back

Go through your validated fields and sort them into two groups.

**Leave on the new default** any field whose validator makes a network request — username availability, coupon codes, address lookup. These are the fields the change was made for, and you get the improvement for free.

**Opt back in** to per-keystroke validation for fields where live feedback is the point and the check is local: password strength meters, character counters, "passwords match" confirmations, format masks. For those, set `validateOn` on the field:

```js
{
  name: 'password',
  validate: passwordStrength,
  validateOn: 'input',   // restores 2.x behaviour for this field
}
```

`validateOn` is per field, so you can restore the old behaviour exactly where you want it without giving up the improvement everywhere else.

If you need to get back to 2.x behaviour quickly and sort it out later, setting `validateOn: "input"` on every validated field reproduces the old timing. Treat that as a stopgap rather than the end state — it reintroduces the request-per-character problem on any server-backed field.

## Step 4: Replace `strictValidation`

`strictValidation` is renamed to `validation`, which now takes a string:

| 2.x | 3.0 |
|---|---|
| `strictValidation: true` | `validation: "strict"` |
| `strictValidation: false` | `validation: "loose"` |
| — | `validation: "off"` |

`"off"` is new; there was no way to express it in 2.x.

The boolean still works in 3.0 and behaves exactly as before, but logs a deprecation warning. It is removed in 4.0. This is not urgent, but it's a mechanical find-and-replace, so it's worth doing while you're already in the file.

## No action needed: validator signature

Validators now receive a second argument:

```js
function validator(value, context) { ... }
```

`context` carries the other field values, so a validator can finally make decisions based on the rest of the form — a date that must fall after another date, a field required only when a checkbox is ticked.

Existing one-argument validators are unaffected and need no changes. Adopt the second argument only where you want it.

## Checklist

- [ ] Node 18+ locally, in CI, and in production
- [ ] `npx formkit migrate-config` run, output reviewed, `formkit.json` deleted
- [ ] Every validated field reviewed for validation timing; `validateOn: "input"` added where live feedback matters
- [ ] `strictValidation` replaced with `validation` (before 4.0)