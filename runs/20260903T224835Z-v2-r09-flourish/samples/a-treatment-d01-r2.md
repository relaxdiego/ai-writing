# datestamp

Renames photo files so the filename begins with the date the photo was taken, read from the photo's own metadata: `beach.jpg` becomes `2026-03-11-beach.jpg`. Sorting a folder by name then sorts it by date, in any file manager, with no catalogue or database in between.

## Install

```
pip install datestamp
```

## Renaming a folder

```
datestamp run ./photos
```

By default this is a dry run: it prints the renames it would make and changes nothing on disk. Read that list, and when it looks right, repeat the command with `--apply` to carry the renames out.

```
datestamp run ./photos --apply
```

The date comes from the metadata the camera wrote into the file, not from the filesystem timestamp, which copying or editing can overwrite. A photo whose metadata carries no date is left alone and listed at the end of the run, so the files that need your own judgement are collected in one place rather than silently passed over.

Two photos can compete for the same new name, most often when they were taken on the same day and already share a name. The first one to be renamed takes the plain form and the rest get a counter appended:

```
2026-03-11-beach.jpg
2026-03-11-beach-2.jpg
2026-03-11-beach-3.jpg
```

## Undoing a run

Keep `.datestamp-log`, or the renames cannot be reversed.

Every `--apply` run records the old and new name of each file it touched in a file called `.datestamp-log`, written into the folder it worked on. `datestamp undo` reads that file back and restores the original names:

```
datestamp undo ./photos
```

Because the log is the only record of what the names used to be, deleting it, or moving the photos elsewhere without it, leaves the undo with nothing to work from.

## What it covers

- Only `.jpg` and `.heic` files are considered; anything else in the folder is ignored and left untouched.
- Only the folder you name is read. Pass `--recursive` to descend into its subfolders as well, in which case each folder gets its own `.datestamp-log`.