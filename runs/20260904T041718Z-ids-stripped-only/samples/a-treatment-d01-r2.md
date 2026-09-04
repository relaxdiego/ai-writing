# datestamp

Rename photo files so the filename starts with the date the photo was taken, read from the photo's own metadata. A file called `beach.jpg` shot on 11 March 2026 becomes `2026-03-11-beach.jpg`, so sorting the folder by name sorts it by date.

## Install

```
pip install datestamp
```

## Usage

```
datestamp run ./photos
```

By default this changes nothing. It prints the renames it would make and exits, so you can read the plan before committing to it. When the plan looks right, run it again with `--apply`:

```
datestamp run ./photos --apply
```

`datestamp` looks at `.jpg` and `.heic` files only, and it stays in the folder you point it at. Pass `--recursive` to descend into subfolders.

## Photos without a date

A photo whose metadata carries no date is left alone. Every skipped file is listed at the end of the run, so nothing disappears quietly from the output: if a file is neither renamed nor listed as skipped, it wasn't a `.jpg` or `.heic` in the first place.

## Name collisions

Several photos taken on the same day can easily reduce to the same new name. When that happens the first file keeps the plain name and the rest get a counter appended, giving `2026-03-11-beach.jpg`, `2026-03-11-beach-2.jpg`, `2026-03-11-beach-3.jpg`. No existing file is ever overwritten.

## Undo

Each applied run records the old and new name of every file it touched in a `.datestamp-log` file inside the folder. To put the names back:

```
datestamp undo ./photos
```

`undo` reads that log, so it works only in a folder where `datestamp` has been applied and the log is still present. Deleting `.datestamp-log` deletes your ability to reverse the run.

## Options

| Option | Effect |
| --- | --- |
| `--apply` | Perform the renames. Without it, `run` only prints what it would do. |
| `--recursive` | Also process photos in subfolders. |

## Supported formats

`.jpg` and `.heic`. Other files in the folder, including other image formats, are ignored.