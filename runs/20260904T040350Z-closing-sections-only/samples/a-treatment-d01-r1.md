# datestamp

`datestamp` renames photo files so the filename begins with the date the photo was taken, read from the photo's own metadata. A file called `beach.jpg` shot on 11 March 2026 becomes `2026-03-11-beach.jpg`. Once a folder has been through it, sorting by name sorts by date, in any file manager, with nothing to keep in step but the filenames themselves.

## Install

```
pip install datestamp
```

## Renaming a folder

```
datestamp run ./photos
```

This prints the renames it would make and changes nothing on disk. Read the list; when it says what you expected, run the same command again with `--apply`:

```
datestamp run ./photos --apply
```

The dry run is the default because a rename is the entire operation, and the cheapest place to catch a wrong date or an unexpected file is before anything has moved. Nothing is written without `--apply`.

`run` looks only at the files sitting directly in the folder you name. To descend into subfolders, add `--recursive`:

```
datestamp run ./photos --recursive --apply
```

## Photos with no date

A photo whose metadata carries no date is left exactly as it is, and its name is printed at the end of the run in a list of skipped files. Screenshots, exported images and anything that has passed through a tool that strips metadata will usually turn up there. Because they are collected rather than merely ignored, a folder that comes out half-renamed tells you which files to look at.

## Names that collide

Two photos taken on the same day whose names would otherwise match are separated by a counter on the second and later files:

```
2026-03-11-beach.jpg
2026-03-11-beach-2.jpg
2026-03-11-beach-3.jpg
```

## Undoing a run

`datestamp` records the old and new name of every file it renames in a file called `.datestamp-log`, kept in the folder it worked on. To put the names back:

```
datestamp undo ./photos
```

The undo reads that log, so it is worth leaving `.datestamp-log` in place for as long as you might want to reverse the run. Deleting it does no harm to the photos, but it does remove the record that `undo` works from.

## What it handles

Files ending `.jpg` and `.heic`. Everything else in the folder is left alone and does not appear in the output.