# datestamp

`datestamp` renames photo files so the filename begins with the date the photo was taken, read from the photo's own metadata rather than from the filesystem timestamp. A file named `beach.jpg` shot on 11 March 2026 becomes `2026-03-11-beach.jpg`. Sorting a folder by name then puts it in chronological order in any file manager, on any machine, without a database or a sidecar file to carry around.

## Install

```
pip install datestamp
```

## Renaming a folder

Point it at a folder:

```
datestamp run ./photos
```

By default this changes nothing. It prints the rename it would perform for each photo and exits, so you can read the list and confirm it is what you meant. When you are satisfied, run the same command with `--apply`:

```
datestamp run ./photos --apply
```

Only the folder you name is examined. To descend into subfolders, add `--recursive`; each photo is then renamed in the folder where it already sits, and nothing is moved between folders.

## What happens to each photo

A photo whose metadata contains no capture date is left alone. Skipped files are collected and listed at the end of the run rather than reported inline, so a folder with a handful of undated scans still gives you a readable summary instead of a list broken up by warnings.

Photos taken on the same day frequently produce the same target name. When that happens the first file keeps the plain name and each subsequent one gets a counter before the extension:

```
2026-03-11-beach.jpg
2026-03-11-beach-2.jpg
2026-03-11-beach-3.jpg
```

Both `.jpg` and `.heic` are handled. Any other file in the folder, including RAW files, video and existing sidecars, is ignored entirely.

## Undoing a run

Every applied run writes the old and new name of each renamed file to `.datestamp-log` in the folder. To put the names back:

```
datestamp undo ./photos
```

This reads the log and restores each file to the name it had before. Keep `.datestamp-log` in place if you may want to reverse the run; deleting it leaves the renames in effect with no record of what the originals were called.