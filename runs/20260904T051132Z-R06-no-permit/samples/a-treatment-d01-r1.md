# datestamp

`datestamp` renames photo files so the filename starts with the date the photo was taken, read from the photo's own metadata. `beach.jpg` taken on 11 March 2026 becomes `2026-03-11-beach.jpg`, so a folder sorted by name is also sorted by date.

## Install

```
pip install datestamp
```

## Usage

```
datestamp run ./photos
```

By default this changes nothing. It prints the renames it would make and stops, so you can read them over first. Add `--apply` to carry them out:

```
datestamp run ./photos --apply
```

`datestamp` handles `.jpg` and `.heic` files, and looks only at the folder you name. Pass `--recursive` to descend into subfolders as well.

## Commands and options

| Command | Effect |
| --- | --- |
| `datestamp run <folder>` | Print the renames that would be made |
| `datestamp run <folder> --apply` | Perform the renames |
| `datestamp undo <folder>` | Restore the previous names from the log |

| Option | Effect |
| --- | --- |
| `--apply` | Rename the files instead of only printing what would change |
| `--recursive` | Include subfolders of the given folder |

## Photos without a date

A photo whose metadata carries no date is left alone. Nothing is guessed from the file's modification time or its current name. Every skipped file is listed at the end of the run, so the report tells you both what was renamed and what was passed over.

## Two photos, one name

If two photos would end up with the same new name, a counter goes on the end: the second becomes `2026-03-11-beach-2.jpg`, the third `2026-03-11-beach-3.jpg`, and so on. No existing file is overwritten.

## Undoing a run

Each applied run records the old and new name of every file it touched in a file called `.datestamp-log`, kept in the folder it worked on. To put the names back:

```
datestamp undo ./photos
```

The log travels with the folder rather than with the tool, so an undo depends on it still being there. Deleting `.datestamp-log`, or moving the renamed photos somewhere else, leaves nothing for `undo` to read.