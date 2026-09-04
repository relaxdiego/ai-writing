# datestamp

`datestamp` renames photo files so the filename begins with the date the photo was taken, read from the photo's own metadata rather than from the file's timestamp on disk. A picture called `beach.jpg` shot on 11 March 2026 becomes `2026-03-11-beach.jpg`, so that sorting a folder by name sorts it by date.

## Install

```
pip install datestamp
```

## Renaming a folder

```
datestamp run ./photos
```

This changes nothing by default. It prints the renames it would make and exits, so you can read the list before committing to it. Once the list looks right, run it again with `--apply`:

```
datestamp run ./photos --apply
```

`datestamp` handles `.jpg` and `.heic` files and leaves everything else in the folder alone. It also stays in the folder you name; pass `--recursive` to descend into subfolders.

A photo whose metadata carries no date is skipped and listed at the end of the run, in the preview and after `--apply` alike. Nothing is renamed on a guess.

## Names that collide

Where two photos would end up with the same new name, `datestamp` appends a counter to each one after the first:

```
2026-03-11-beach.jpg
2026-03-11-beach-2.jpg
2026-03-11-beach-3.jpg
```

## Undoing a run

Every applied run writes a file called `.datestamp-log` into the folder, recording each old name against the new one it was given. To put the old names back:

```
datestamp undo ./photos
```

The log is the only record of the original names, so keep it with the photos it describes. If `.datestamp-log` is deleted, or the renamed photos are moved to a folder that has no log of its own, `undo` has nothing to read from and the original names are gone.