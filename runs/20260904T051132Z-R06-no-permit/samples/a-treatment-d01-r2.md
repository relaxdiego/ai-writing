Here is the README.

---

# datestamp

Rename photo files so the filename starts with the date the photo was taken:

```
beach.jpg  →  2026-03-11-beach.jpg
```

The date is read from the photo's own metadata, so it survives copying, syncing and backup — unlike the file's modification time, which is reset by all three.

## Install

```
pip install datestamp
```

## Quick start

```
datestamp run ./photos
```

This is a dry run: it prints the renames it would make and changes nothing on disk. When the list looks right, repeat the command with `--apply` to carry it out:

```
datestamp run ./photos --apply
```

## Commands and options

| Command / option | What it does |
| --- | --- |
| `datestamp run DIR` | Show the renames for `DIR` without touching anything |
| `datestamp run DIR --apply` | Perform the renames |
| `datestamp run DIR --recursive` | Include subfolders (off by default) |
| `datestamp undo DIR` | Restore the names recorded in `DIR/.datestamp-log` |

## How names are built

The date is prefixed to the existing filename in `YYYY-MM-DD-` form, and the rest of the name is left alone. If two photos in the same folder would end up with the same name, a counter is appended to the second and subsequent ones — `2026-03-11-beach.jpg`, `2026-03-11-beach-2.jpg`, `2026-03-11-beach-3.jpg` — so no file is ever overwritten by another.

## Photos without a date

A photo whose metadata carries no capture date is left untouched, and every such file is listed at the end of the run. Screenshots, images exported by editors that strip metadata, and files recovered from a card are the usual cases. Nothing is guessed from the filesystem timestamp.

## Undoing a run

Each applied run writes `.datestamp-log` into the folder it worked on, recording the old and new name of every file it renamed. `datestamp undo ./photos` reads that file and puts the names back.

Undo depends entirely on that log. If `.datestamp-log` is deleted, or the folder is moved without it, or the files are renamed by hand afterwards, the original names cannot be recovered. Keep the log alongside the photos until you are satisfied with the result.

## Scope

Only `.jpg` and `.heic` files are considered; anything else in the folder is ignored and left in place. Subfolders are not visited unless you pass `--recursive`.