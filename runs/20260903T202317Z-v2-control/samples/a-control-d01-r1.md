Here's the README. I've kept it to what you specified — no invented flags, config options, or platform claims.

```markdown
# datestamp

Rename photo files so the filename starts with the date the photo was taken, read
from the photo's own metadata.

```
beach.jpg  ->  2026-03-11-beach.jpg
```

## Install

```
pip install datestamp
```

## Usage

Preview the renames in a folder:

```
datestamp run ./photos
```

By default `run` changes nothing — it prints the renames it would make so you can
check them first. To actually perform them, add `--apply`:

```
datestamp run ./photos --apply
```

Only `.jpg` and `.heic` files are considered. Subfolders are ignored unless you
pass `--recursive`:

```
datestamp run ./photos --recursive --apply
```

## Photos without a date

If a photo has no date in its metadata, datestamp skips it and leaves the file
untouched. Skipped files are listed together at the end of the run, so you can
see what was left behind without scrolling back through the output.

## Name collisions

If two photos would end up with the same name, datestamp appends a counter to
keep them distinct:

```
2026-03-11-beach.jpg
2026-03-11-beach-2.jpg
2026-03-11-beach-3.jpg
```

## Undo

Each time datestamp renames files, it records the old and new names in a file
called `.datestamp-log` in that folder. To put the names back:

```
datestamp undo ./photos
```

`undo` reads `.datestamp-log` from the folder you give it. If that file has been
deleted or moved, the renames can't be reversed — keep it around until you're
sure you want to make the change permanent.

## Commands

| Command | What it does |
| --- | --- |
| `datestamp run <folder>` | Show the renames that would be made. Changes nothing. |
| `datestamp run <folder> --apply` | Perform the renames. |
| `datestamp run <folder> --recursive` | Include subfolders. |
| `datestamp undo <folder>` | Restore the previous names from `.datestamp-log`. |
```

Two small judgment calls worth flagging: I placed the collision counter before the extension (`2026-03-11-beach-2.jpg`), and I described `undo` as reading the log from the folder passed to it. Tell me if either differs from the actual behaviour.

I printed this rather than writing it to disk — the working directory is your `ai-writing` scratch repo, not a `datestamp` checkout. Say the word and I'll write it wherever the project actually lives.