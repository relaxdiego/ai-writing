# datestamp

`datestamp` renames photo files so the filename begins with the date the photo was taken, read from the photo's own metadata rather than from the file's timestamp on disk. A folder of camera names sorts into chronological order the moment the rename lands, and stays that way after copying, syncing or re-downloading, because the date now lives in the name.

```
IMG_4471.jpg  ->  2026-03-11-beach.jpg
```

## Installing

```
pip install datestamp
```

## Renaming a folder

Point the `run` command at a folder:

```
datestamp run ./photos
```

This is a dry run. It prints every rename it would make and changes nothing on disk, so you can read the plan before committing to it. When the plan looks right, repeat the command with `--apply` to perform the renames:

```
datestamp run ./photos --apply
```

Only `.jpg` and `.heic` files are considered. Everything else in the folder is left alone, and subfolders are ignored unless you pass `--recursive`, which walks the whole tree beneath the folder you named.

## Photos without a date

A photo whose metadata carries no capture date is skipped rather than guessed at. Skipped files keep their original names and are listed together at the end of the run, so a folder that came out of an editor or a messaging app tells you plainly which files it could not date instead of burying that in the middle of the output.

## Name collisions

Two photos taken on the same day would otherwise compete for the same name. When that happens, `datestamp` appends a counter to the later ones:

```
2026-03-11-beach.jpg
2026-03-11-beach-2.jpg
2026-03-11-beach-3.jpg
```

## Undoing a run

Every applied run writes a file called `.datestamp-log` in the folder it worked on, recording the old and new name of each file it renamed. To put the names back, run:

```
datestamp undo ./photos
```

`undo` reads `.datestamp-log` from that folder and reverses the renames it finds there. The log is the whole record of what happened, so deleting it or moving the photos to another folder without it leaves nothing to undo from.