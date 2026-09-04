# datestamp

`datestamp` renames photo files so the filename begins with the date the photo was taken, read from the photo's own metadata. `beach.jpg` taken on 11 March 2026 becomes `2026-03-11-beach.jpg`. Once a folder has been through it, sorting by name sorts by date, and the date survives being copied to a drive, attached to an email, or opened by a program that knows nothing about EXIF.

## Install

```
pip install datestamp
```

## Running it

```
datestamp run ./photos
```

That command changes nothing. It prints the rename it would perform for each file so you can read the list first, which matters because renaming a folder of photos is tedious to reverse by hand. When the list looks right, run it again with `--apply`:

```
datestamp run ./photos --apply
```

Only `.jpg` and `.heic` files are considered, and only the ones sitting directly in the folder you name. Pass `--recursive` to descend into subfolders.

| Invocation | Effect | Touches files |
| --- | --- | --- |
| `datestamp run ./photos` | Prints the planned renames | No |
| `datestamp run ./photos --apply` | Performs the renames and writes `.datestamp-log` | Yes |
| `datestamp run ./photos --recursive` | Includes subfolders | Only with `--apply` |
| `datestamp undo ./photos` | Restores the previous names from `.datestamp-log` | Yes |

## Skips and collisions

A photo with no date in its metadata is left alone, and every such file is listed together at the end of the run. Screenshots, images that have been through a messaging app, and scans usually land here, so the closing list tells you what still needs a date rather than letting those files disappear quietly into an otherwise successful run.

Where two photos would arrive at the same new name, the first keeps the plain name and the rest take a counter before the extension:

```
2026-03-11-beach.jpg
2026-03-11-beach-2.jpg
2026-03-11-beach-3.jpg
```

## Undoing a run

Every applied run records the old and new name of each file it touched in `.datestamp-log`, kept in the folder that was renamed. `datestamp undo ./photos` reads that file and puts the names back. The log is the only record of what the original names were, so leave it in place alongside the photos; if the folder is moved or copied somewhere without it, there is nothing left to undo from.