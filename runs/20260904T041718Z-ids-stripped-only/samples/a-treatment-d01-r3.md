# datestamp

`datestamp` renames photo files so the filename starts with the date the photo was taken, read from the photo's own metadata. A file called `beach.jpg` shot on 11 March 2026 becomes `2026-03-11-beach.jpg`, so an alphabetical listing of a folder is also a chronological one.

## Install

```
pip install datestamp
```

## Usage

Point it at a folder:

```
datestamp run ./photos
```

This is a dry run. It prints the rename it would perform for each photo and changes nothing on disk, so you can read the list over before committing to it. When the plan looks right, repeat the command with `--apply`:

```
datestamp run ./photos --apply
```

Only `.jpg` and `.heic` files are considered, and only those sitting directly in the folder you named. Pass `--recursive` to descend into subfolders as well.

## Options

| Option | Effect |
| --- | --- |
| `--apply` | Perform the renames. Without it, `run` only prints what it would do. |
| `--recursive` | Also process photos in subfolders of the given folder. |

## Photos without a date

A photo whose metadata carries no capture date cannot be renamed, so `datestamp` leaves it exactly as it is and collects it in a list printed after the main output. Nothing is guessed from the file's modification time, because that timestamp usually records when the file was last copied rather than when the shutter fired.

## Name collisions

Two photos taken on the same day and sharing the same original name would resolve to the same new name. Rather than overwrite one with the other, `datestamp` appends a counter to each name after the first: the second becomes `2026-03-11-beach-2.jpg`, the third `2026-03-11-beach-3.jpg`, and so on. The counter appears in the dry-run output too, so you can see which files were affected before applying anything.

## Undoing a run

Every applied run writes the old and new name of each renamed file to a `.datestamp-log` file in the folder it operated on. To reverse the renames, run:

```
datestamp undo ./photos
```

`undo` reads that log and restores the previous names. Because the log lives in the folder, keep it there for as long as you might want to go back; if the folder is moved, move the log with it.