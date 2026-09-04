# datestamp

`datestamp` renames photo files so that each filename starts with the date the photo was taken. The date comes from the photo's own metadata, not from the file's timestamp, so it survives copying, syncing and re-downloading. A photo called `beach.jpg` taken on 11 March 2026 becomes `2026-03-11-beach.jpg`, which means a plain alphabetical listing of a folder is also a listing in chronological order.

## Install

```
pip install datestamp
```

## Usage

Point it at a folder:

```
datestamp run ./photos
```

By default this changes nothing. It prints the rename it would perform for each photo and exits, so you can read the list and decide. When the list looks right, run it again with `--apply`:

```
datestamp run ./photos --apply
```

## Options

| Option | Effect |
| --- | --- |
| `--apply` | Perform the renames. Without it, `run` only prints what it would do. |
| `--recursive` | Descend into subfolders. Without it, only files directly in the given folder are considered. |

## What gets renamed

Only `.jpg` and `.heic` files are considered. Everything else in the folder is left alone, including video, RAW files and sidecar files.

Photos whose metadata carries no date are skipped rather than guessed at, and every skipped file is listed together at the end of the run so you can see what was left behind in one place.

If two photos in the same folder would end up with the same new name, the second and subsequent files get a counter before the extension: `2026-03-11-beach.jpg`, `2026-03-11-beach-2.jpg`, `2026-03-11-beach-3.jpg`. No file is ever overwritten.

## Undoing a run

Each applied run records the old and new name of every file it touched in a file called `.datestamp-log`, kept in the folder it was run on. To put the names back:

```
datestamp undo ./photos
```

`undo` reads `.datestamp-log` from that folder and reverses the renames it records. Because the log lives alongside the photos, moving or deleting it leaves the run with nothing to reverse it, so keep it in place until you are satisfied with the result.