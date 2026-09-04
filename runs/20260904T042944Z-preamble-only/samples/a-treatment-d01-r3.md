# datestamp

`datestamp` renames photo files so the filename begins with the date the photo was taken, read from the photo's own metadata rather than from the filesystem timestamp. A file called `beach.jpg` shot on 11 March 2026 becomes `2026-03-11-beach.jpg`, which means a plain alphabetical listing of the folder is also a chronological one.

## Install

```
pip install datestamp
```

## Use

Point it at a folder:

```
datestamp run ./photos
```

By default this changes nothing. It prints the renames it would make and stops, so you can read the list, decide it looks right, and only then commit to it. Add `--apply` to perform the renames:

```
datestamp run ./photos --apply
```

The dry run and the real run report the same thing:

```
beach.jpg          ->  2026-03-11-beach.jpg
DSC_0148.heic      ->  2026-03-11-DSC_0148.heic
sunset.jpg         ->  2026-03-12-sunset.jpg
```

Only `.jpg` and `.heic` files are considered. Everything else in the folder is left alone, and subfolders are ignored unless you pass `--recursive`.

## Options

| Flag | Effect |
| --- | --- |
| `--apply` | Perform the renames instead of only printing them |
| `--recursive` | Descend into subfolders |

## Photos without a date

A photo whose metadata carries no capture date cannot be stamped, so `datestamp` skips it and lists it at the end of the run. The list is there to be acted on: those files keep their original names, and running the tool again will skip them again until the metadata is fixed or you rename them yourself.

## Name collisions

When two photos would end up with the same name, `datestamp` appends a counter to the second and any that follow, giving `2026-03-11-beach.jpg`, `2026-03-11-beach-2.jpg`, `2026-03-11-beach-3.jpg`. No existing file is ever overwritten.

## Undo

Every applied run writes what it did to a file called `.datestamp-log` in the folder it worked on, recording the old and new name of each file. A dry run changes nothing and writes nothing. To reverse the last run, point `undo` at the same folder:

```
datestamp undo ./photos
```

This reads the log and puts the old names back. Because the log is the only record of what the original names were, deleting or moving `.datestamp-log` leaves nothing to undo from, so keep it in the folder for as long as you might want to reverse the rename.