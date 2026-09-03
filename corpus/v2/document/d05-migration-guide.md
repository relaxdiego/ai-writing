---
id: d05
register: document
name: Migration guide
---
Write a migration guide for the following change.

Our library `formkit` is releasing version 3.0. Users are on 2.x.

The configuration file moves from `formkit.json` to `formkit.config.js`, because people needed to compute values and JSON cannot. A command, `npx formkit migrate-config`, converts the old file automatically and is expected to handle almost every case.

The option `strictValidation` is renamed to `validation: "strict" | "loose" | "off"`. The old boolean still works in 3.0 but prints a warning, and will be removed in 4.0. `true` becomes `"strict"` and `false` becomes `"loose"`. There was no previous way to express `"off"`.

Field validators used to receive `(value)` and now receive `(value, context)`, where context carries the other field values. Existing one-argument validators keep working unchanged.

The breaking change with no automatic fix: validators used to run on every keystroke, and now run when a field loses focus, or on submit. Anyone relying on per-keystroke validation must pass `validateOn: "input"` on that field. This was changed because the old behaviour made forms with server-side checks fire a request per character.

Node 16 support is dropped; 18 or later is required.
