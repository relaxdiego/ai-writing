# Migrating from formkit 2.x to 3.0

One change in 3.0 alters your forms' behaviour without raising an error or printing a warning: validators no longer run on every keystroke. If any part of your application depends on validation firing as the user types, read the last section before you upgrade, because nothing in the toolchain will tell you it has changed.

Everything else in this release either converts automatically or keeps working under a deprecation notice, so the upgrade is mostly mechanical.

## Node 18 is now the minimum

3.0 drops support for Node 16. Move your development machines, CI images, and deployment targets to Node 18 or later before you install the new version, otherwise the install itself will fail and you will be debugging the wrong problem.

## The configuration file becomes JavaScript

`formkit.json` is replaced by `formkit.config.js`. The reason is that configuration frequently needs to be computed: an API base URL that differs per environment, a field list derived from a schema, a validator imported from your own code. JSON cannot express any of that, so people were generating the JSON file from a script and checking the generated artifact into the repository.

Run the converter from the root of your project:

```
npx formkit migrate-config
```

It reads `formkit.json`, writes `formkit.config.js`, and handles almost every configuration in practice. What it produces is ordinary JavaScript with a default export, so once it has run you can edit the result freely:

```js
// formkit.config.js
export default {
  validation: "strict",
  fields: {
    email: { required: true },
  },
}
```

Read the generated file before you delete the old one, and confirm that every key from your `formkit.json` made it across. If something did not convert, it will be missing rather than wrong, and comparing the two files side by side is the fastest way to see it. Once you are satisfied, remove `formkit.json`; leaving both in place is not an error, but only the `.js` file is read.

## `strictValidation` becomes `validation`

The boolean `strictValidation` is replaced by a `validation` option taking `"strict"`, `"loose"`, or `"off"`. Write `"strict"` where you had `true` and `"loose"` where you had `false`. The third value, `"off"`, disables validation entirely and has no equivalent in 2.x, so nothing in your existing configuration should convert to it.

The old boolean still works in 3.0. It prints a deprecation warning and will be removed in 4.0, so treat the warning as work you have scheduled rather than work you can ignore. `migrate-config` performs this rename for you as part of the config conversion; you only need to do it by hand if you set the option somewhere other than the configuration file.

## Validators receive a second argument

Field validators are now called with `(value, context)`, where `context` carries the values of the other fields in the form. This makes cross-field rules possible without threading state through a closure or reaching into the DOM:

```js
// 2.x signature, unchanged and still valid in 3.0
const notEmpty = (value) => value.trim().length > 0

// 3.0 only
const matchesPassword = (value, context) => value === context.password
```

Existing one-argument validators keep working exactly as they did. JavaScript ignores the extra argument, so there is nothing to migrate here and no deprecation attached to the old form. Adopt the second parameter when you have a rule that needs it.

## Validators now run on blur and on submit

In 2.x, a field's validators ran on every keystroke. In 3.0 they run when the field loses focus, and again when the form is submitted. This was changed because the old behaviour made any validator that talked to a server issue one request per character typed, which is expensive for you and, on a slow connection, visibly broken for the user.

There is no automatic fix for this one, because whether per-keystroke validation was load-bearing is a question about your product rather than your code. To restore the old timing for a field, set `validateOn: "input"` on it:

```js
{
  name: "coupon",
  validateOn: "input",
  validators: [checkFormat],
}
```

The fields most likely to need this are the ones where the user expects feedback while typing rather than after leaving the field: password strength meters, character counters, live format hints, anything that turns a border green as the input becomes valid. Those will now stay silent until focus moves away, and no error will be raised to tell you so.

Fields validated against a server are the opposite case. A username availability check or a coupon lookup is precisely what the new default was designed to fix, so leave those on the default and let them fire on blur.

The practical way to find affected fields is to search your codebase for validators that are asynchronous or that touch the network, note that those are already correct, then walk the remaining forms and ask which of them showed the user something as they typed. That list is your `validateOn: "input"` list.