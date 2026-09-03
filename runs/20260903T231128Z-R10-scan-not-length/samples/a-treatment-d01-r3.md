# datestamp

`datestamp` renames photo files so the filename starts with the date the photo was taken, read from the photo's own metadata. A file called `beach.jpg` shot on 11 March 2026 becomes `2026-03-11-beach.jpg`, so sorting a folder by name sorts it by date.

## Install

```
pip install datestamp
```

## Usage

Point it at a folder:

```
datestamp run ./photos
```

By default this changes nothing. It reads the metadata, prints the rename it would make for each photo, and exits, so you can check the result before committing to it. When the list looks right, run it again with `--apply`:

```
datestamp run ./photos --apply
```

| Flag | Effect |
| --- | --- |
| `--apply` | Perform the renames. Without it, `run` is a preview and the folder is untouched. |
| `--recursive` | Descend into subfolders. By default only files sitting directly in the named folder are considered. |

## Skipped files and name collisions

A photo whose metadata carries no date cannot be renamed, so `datestamp` leaves it alone and collects it in a list printed at the end of the run. Nothing is guessed from the file's modification time.

When two photos in the same folder would end up with the same name, the second gets a counter appended before the extension, the third the next counter, and so on: `2026-03-11-beach.jpg`, `2026-03-11-beach-2.jpg`, `2026-03-11-beach-3.jpg`.

## Undoing a run

Each `--apply` run writes the old and new name of every renamed file to `.datestamp-log` in that folder. To put the names back:

```
datestamp undo ./photos
```

`undo` reads that log file, so keep it if you may want to reverse the run. Deleting it leaves the renames in place with no record of what the originals were called.

## Limits

Only `.jpg` and `.heic` files are handled. Anything else in the folder is ignored, including other image formats and raw files.