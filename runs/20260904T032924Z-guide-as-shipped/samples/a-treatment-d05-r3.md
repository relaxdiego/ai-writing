# Migrating from formkit 2.x to 3.0

One change in this release alters how your forms behave without printing an error or a warning: validators no longer run on every keystroke. Everything else in 3.0 is either converted for you by a command or keeps working as it did. Read the section on validation timing even if you skip the rest.

## At a glance

| Change | 2.x | 3.0 | How to migrate | Breaks in 3.0? |
|---|---|---|---|---|
| Config file | `formkit.json` | `formkit.config.js` | `npx formkit migrate-config` | Yes, until you run the command |
| Validation mode | `strictValidation: true \| false` | `validation: "strict" \| "loose" \| "off"` | Rename one option | No; warns until 4.0 |
| Validator arguments | `(value)` | `(value, context)` | Nothing required | No |
| When validators run | Every keystroke | Blur and submit | Set `validateOn` per field | Yes, silently |
| Node | 16 or later | 18 or later | Upgrade the runtime | Yes |

## Node 18

Node 16 is no longer supported. Upgrade your local runtime, your CI images, and your deployment target to Node 18 or later before you install 3.0, since an install on 16 will fail rather than degrade.

## The configuration file

`formkit.json` is replaced by `formkit.config.js`. The reason is that a JSON file cannot compute anything, so configuration that depended on an environment variable, a shared constant, or a value read at startup had to be worked around outside the file. A JavaScript module can just calculate it.

Run the converter from the root of your project:

```
npx formkit migrate-config
```

It reads your existing `formkit.json` and writes `formkit.config.js` with the same keys, so a config that was

```json
{ "strictValidation": true }
```

becomes a module exporting the equivalent object. The command is expected to handle almost every 2.x config, but "almost every" is not "every": read the file it produces, and keep the old JSON in version control until you have confirmed the new one loads. If you have a config that the command cannot convert, the resulting file is still an ordinary JavaScript module, so you can finish it by hand.

Once the new file exists, delete `formkit.json`. Leaving both in place is not a supported configuration.

## `strictValidation` becomes `validation`

The boolean is replaced by a three-value option. `true` becomes `"strict"` and `false` becomes `"loose"`:

```js
// 2.x
{ strictValidation: true }

// 3.0
{ validation: "strict" }
```

The third value, `"off"`, has no 2.x equivalent. It disables validation entirely, which previously could only be approximated by removing your validators.

The old boolean still works in 3.0. It prints a deprecation warning on startup and will be removed in 4.0, so treat the warning as a task rather than noise. In particular, the config converter reproduces the keys it finds, so if your 2.x file set `strictValidation`, expect the warning to appear after migrating the file and rename the option yourself.

## Validators now receive a context argument

Field validators are called with `(value, context)` instead of `(value)`. The context carries the other field values, which makes cross-field checks possible without reaching outside the validator:

```js
// 3.0
const matchesPassword = (value, context) => value === context.password
```

Nothing is required of you here. A validator declared with one parameter ignores the second argument and behaves exactly as it did in 2.x, so existing validators need no edit. This is an addition, listed so you know the capability is there.

## Validators now run on blur and submit

This is the change with no automatic fix, and the one that will not announce itself.

In 2.x, a field's validators ran on every keystroke. In 3.0 they run when the field loses focus, and again on submit. The behaviour changed because a validator that calls a server fired one request per character typed, which is expensive for you and worse for whoever you were calling.

To restore per-keystroke validation, set `validateOn` on the field:

```js
{ name: "username", validateOn: "input" }
```

`validateOn` is set per field. There is no global switch back, and that is deliberate: applying `"input"` across a whole form is how the original problem was created.

### Finding the fields that need it

Nothing in your code will fail, so you have to go looking. Work through your fields and ask what the validator is for:

- **Fields whose feedback is the point of typing.** Password strength meters, character counters, live "passwords match" checks, and format hints that guide someone mid-entry all become useless if they only appear after the field is left. These need `validateOn: "input"`.
- **Fields whose validator calls a server.** Username availability, coupon codes, address lookup. Leave these on the new default. They are the reason it changed, and blur-time validation is what you wanted all along.
- **Fields with plain local checks.** Required, length, regex, numeric range. Blur and submit are almost always fine, and the form is quieter for it, since a required field no longer reports itself empty while you are still typing into it.

Anything you are unsure about is safer left on the default and revisited, because the failure mode is a message arriving a moment later than before rather than a flood of requests.

Test the change by typing into a form and tabbing away rather than by running your unit tests. A validator tested by calling it directly passes identically under both versions; the timing is a property of the form, not of the function.