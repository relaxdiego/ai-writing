# datestamp

`datestamp` renames photo files so that each filename begins with the date the photo was taken. The date comes from the photo's own metadata, not from the file's modification time, so it stays correct after the files have been copied between machines or restored from a backup. A photo taken on 11 March 2026 and named `beach.jpg` becomes `2026-03-11-beach.jpg`, and a folder of such files sorts chronologically under any ordinary sort by name.

## Install

```
pip install datestamp
```

## Usage

Point it at a folder:

```
datestamp run ./photos
```

By default this is a dry run: it prints the rename it would perform for each file and leaves the folder untouched. Read the output, and when it looks right, repeat the command with `--apply` to carry the renames out.

```
datestamp run ./photos --apply
```

Only `.jpg` and `.heic` files are considered, and only those directly inside the folder you name. Pass `--recursive` to descend into subfolders as well; each file is still renamed in place, in the folder where it was found.

## Photos without a date

A photo whose metadata carries no capture date is left alone. `datestamp` collects these as it goes and lists them at the end of the run, so the files it could not handle are reported together rather than buried in the output. This happens with images that have been through editors or messaging apps that strip metadata, and the remedy is to supply the date by renaming those few files yourself.

## Name collisions

Two photos taken on the same day can easily reduce to the same new name. When that happens, `datestamp` appends a counter to all but the first: `2026-03-11-beach.jpg`, then `2026-03-11-beach-2.jpg`, then `2026-03-11-beach-3.jpg`. No existing file is ever overwritten, and the counter is applied during the dry run too, so the printed plan shows the names you will actually get.

## Undoing a run

Every applied run appends to a file called `.datestamp-log` in the folder, recording the old and new name of each file it moved. To reverse the most recent run:

```
datestamp undo ./photos
```

This reads the log and restores the previous names. The log is therefore worth leaving in place: delete it and the renames become permanent, since nothing else records what the files were called before.