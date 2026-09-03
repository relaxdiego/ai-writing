# Migrating from formkit 2.x to 3.0

One change in 3.0 will alter your forms' behaviour without any error or warning to tell you it happened: validators no longer run on every keystroke. They now run when a field loses focus and on submit. Nothing in the upgrade flags the fields this affects, so plan to walk your forms and decide, field by field, whether the new timing is what you want.

The rest of the release is mechanical. A codemod converts your config file, and the two API changes are backward compatible for now.

| Change | Fixed automatically | 2.x code still works in 3.0 |
| --- | --- | --- |
| Node 16 dropped, 18+ required | No | n/a |
| `formkit.json` → `formkit.config.js` | Yes, `npx formkit migrate-config` | No |
| `strictValidation` → `validation` | No | Yes, with a warning; removed in 4.0 |
| Validators receive `(value, context)` | Not needed | Yes, indefinitely |
| Validation runs on blur, not input | No | No |

## Node 18 or later

Do this before anything else, since the 3.0 package will not install on Node 16. If your CI images or deploy targets are pinned to 16, upgrade them in a separate change and let it settle before you touch formkit itself. That keeps a Node upgrade failure from looking like a formkit upgrade failure.

## The config file moves to `formkit.config.js`

JSON could not express a computed value, so configuration is now a JavaScript module. Run the codemod from your project root:

```
npx formkit migrate-config
```

It reads `formkit.json`, writes `formkit.config.js`, and handles almost every case. Review the result rather than accepting it unread: put the generated file through your normal code review, and check that the exported object matches the JSON it came from. Comments and any unusual key names are the places worth a second look.

The generated file is a module with a default export, so anything you want to compute can now be computed:

```js
// formkit.config.js
export default {
  endpoint: process.env.FORMKIT_ENDPOINT ?? "https://api.example.com/forms",
  locale: resolveLocale(),
  validation: "strict",
};
```

If anything outside formkit read `formkit.json` (a CI script, a code generator, a dashboard that parsed your settings), that reader breaks, because the file is now JavaScript rather than data. The codemod does not know about those consumers. Either point them at the new module through an import, or have the config module export a plain object that you serialise for them at build time.

## `strictValidation` becomes `validation`

The boolean is replaced by a three-valued option. `strictValidation: true` becomes `validation: "strict"`, and `strictValidation: false` becomes `validation: "loose"`:

```js
// 2.x
{ strictValidation: true }

// 3.0
{ validation: "strict" }
```

There is a third value, `"off"`, which has no 2.x equivalent. It disables validation entirely rather than relaxing it, which is useful in environments where the server is the only authority you trust.

The old boolean still works in 3.0 and prints a deprecation warning on startup. It is removed in 4.0, so treat the warning as the whole of the work: the rename is a one-line edit per config file, and the codemod does not perform it for you.

## Validators now run on blur and submit

In 2.x a validator ran on every keystroke. A validator that checked a username against the server therefore issued one request per character typed, which is the behaviour this change exists to stop. In 3.0 a field validates when it loses focus, and again when the form is submitted.

Where per-keystroke feedback was the point rather than an accident, ask for it explicitly on that field:

```js
{
  name: "password",
  validators: [strength],
  validateOn: "input",
}
```

Password strength meters, character counters, and live format hints are the cases that usually want `validateOn: "input"`. Anything that talks to a server almost certainly does not, and if you were debouncing a validator in 2.x to keep the request rate down, blur is probably what you were approximating; you can drop the debounce along with the old timing.

The failure mode to watch for in testing is not an error but a delay. A field that used to show its message as the user typed now shows it once they leave the field, and end-to-end tests that assert on a message immediately after typing will fail on timing rather than on content. Read those failures as a report of the new behaviour before you change the assertion, because each one marks a field where a human will notice the difference too.

## Validators receive a second argument

Validators are now called as `(value, context)`, where `context` carries the other fields' values. This lets a validator depend on the rest of the form without reaching outside it:

```js
function confirmPassword(value, context) {
  return value === context.password || "Passwords must match";
}
```

Existing one-argument validators keep working unchanged, in 3.0 and after. JavaScript ignores the extra argument, so there is nothing to migrate here and no deprecation attached to it. Adopt the second parameter in the validators that need it and leave the others as they are.