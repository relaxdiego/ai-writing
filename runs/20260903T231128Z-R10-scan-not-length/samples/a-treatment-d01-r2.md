# datestamp

`datestamp` renames photo files so that the filename starts with the date the photo was taken. The date comes from the photo's own metadata rather than from the file's creation or modification time, so pictures that have been copied between machines, synced through a cloud folder or restored from a backup still get the day they were actually shot. A file called `beach.jpg` taken on 11 March 2026 becomes `2026-03-11-beach.jpg`, which means a folder sorted by name is also sorted by date.

## Install

```
pip install datestamp
```

## Renaming a folder

```
datestamp run ./photos
```

By default this changes nothing: it prints the renames it would make and stops. Read the list, and when it says what you expected, run the same command with `--apply` to carry the renames out.

```
datestamp run ./photos --apply
```

`datestamp` looks at `.jpg` and `.heic` files only, and only at the ones sitting directly in the folder you name. Add `--recursive` to descend into subfolders.

## Photos with no date

A photo whose metadata carries no capture date is left alone, keeping the name it already has. Every skipped file is listed together at the end of the run, so you can see in one place which pictures need a date filled in or a name chosen by hand.

## Two photos, one name

Photos taken on the same day often share a base name, and the obvious new name is then already taken. Rather than overwrite anything, `datestamp` appends a counter to the later files: the first keeps `2026-03-11-beach.jpg`, the second becomes `2026-03-11-beach-2.jpg`, the third `2026-03-11-beach-3.jpg`, and so on.

## Undoing a run

Each applied run writes the old and new name of every file it touched to a `.datestamp-log` file in the folder. To put the original names back, point `undo` at the same folder:

```
datestamp undo ./photos
```

The log is what makes this work, so leave it in place if you might want to reverse the run. Delete it and the renames stand as they are.