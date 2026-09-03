# datestamp

Renames photo files so the filename starts with the date the photo was taken, read from the photo's own metadata.

```
beach.jpg  →  2026-03-11-beach.jpg
```

Sorting a folder by name then sorts it by date.

## Install

```
pip install datestamp
```

## Usage

```
datestamp run ./photos
```

This is a dry run: it prints the renames it would make and changes nothing. To actually rename the files, add `--apply`:

```
datestamp run ./photos --apply
```

Only `.jpg` and `.heic` files are considered. Other files in the folder are left alone.

Subfolders are ignored unless you pass `--recursive`:

```
datestamp run ./photos --recursive --apply
```

## Photos without a date

If a photo has no date in its metadata, `datestamp` skips it — the file is not renamed and not touched — and lists it at the end of the run so you know what was left behind.

## Name collisions

If two photos would end up with the same name, a counter is appended:

```
2026-03-11-beach.jpg
2026-03-11-beach-2.jpg
2026-03-11-beach-3.jpg
```

## Undo

Every applied run records the old and new name of each renamed file in a `.datestamp-log` file inside the folder. To put the names back:

```
datestamp undo ./photos
```

`undo` reads `.datestamp-log` from that folder, so keep the file if you want the option to reverse a run. Deleting it does not affect the photos, only your ability to undo.

## Commands

| Command | What it does |
| --- | --- |
| `datestamp run <folder>` | Show the renames that would be made |
| `datestamp run <folder> --apply` | Perform the renames |
| `datestamp run <folder> --recursive` | Include subfolders |
| `datestamp undo <folder>` | Restore the previous names from `.datestamp-log` |

## Suggested workflow

1. Run without `--apply` and read the output.
2. Check the list of skipped photos at the end.
3. Re-run with `--apply`.
4. If it wasn't what you wanted, `datestamp undo` the folder.