# datestamp

`datestamp` renames photo files so the filename starts with the date the photo was taken, read from the photo's own metadata rather than from the filesystem timestamp. A file called `beach.jpg` shot on 11 March 2026 becomes `2026-03-11-beach.jpg`, so that sorting a folder by name sorts it by date.

## Install

```
pip install datestamp
```

## Usage

Point it at a folder:

```
datestamp run ./photos
```

By default this is a dry run: it prints the renames it would make and changes nothing on disk. Read the output, and when it looks right, repeat the command with `--apply` to carry the renames out.

```
datestamp run ./photos --apply
```

Only `.jpg` and `.heic` files are considered, and only those directly inside the folder you name. Pass `--recursive` to descend into subfolders as well.

## Dates, collisions and skips

The date comes from the photo's embedded metadata. If a photo carries no date there, `datestamp` leaves it alone and lists it at the end of the run, so the files it could not handle are visible in one place rather than scattered through the output.

Where two photos in the same folder would end up with the same name, the first keeps the plain name and the others get a counter appended: `2026-03-11-beach.jpg`, `2026-03-11-beach-2.jpg`, `2026-03-11-beach-3.jpg`.

## Undoing a run

Every applied run writes the old and new name of each file to a `.datestamp-log` file in the folder it worked on. To reverse the renames, run:

```
datestamp undo ./photos
```

This reads that log and restores the previous names. Keep `.datestamp-log` in place if you want the option of undoing; deleting it leaves the renames permanent.

## Reference

| Command | What it does |
| --- | --- |
| `datestamp run DIR` | Print the renames that would be made; change nothing |
| `datestamp run DIR --apply` | Perform the renames and write `.datestamp-log` |
| `datestamp run DIR --recursive` | Include subfolders of `DIR` |
| `datestamp undo DIR` | Restore the names recorded in `DIR/.datestamp-log` |