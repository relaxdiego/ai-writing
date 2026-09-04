# datestamp

`datestamp` renames photo files so that each filename starts with the date the photo was taken, read from the photo's own metadata rather than from the file's timestamps. A photo called `beach.jpg` taken on 11 March 2026 becomes `2026-03-11-beach.jpg`, so that listing a folder alphabetically also puts it in chronological order.

## Install

```
pip install datestamp
```

## Usage

Point it at a folder:

```
datestamp run ./photos
```

By default this changes nothing. It reads the folder, works out what each rename would be, and prints the result for you to check:

```
$ datestamp run ./photos
beach.jpg          -> 2026-03-11-beach.jpg
IMG_4471.heic      -> 2026-03-11-IMG_4471.heic
sunset.jpg         -> 2026-03-12-sunset.jpg

3 to rename, 0 skipped. Re-run with --apply to perform the renames.
```

When the list looks right, run it again with `--apply` to carry the renames out.

## Command reference

| Command | What it does |
| --- | --- |
| `datestamp run <folder>` | Show the renames without making them |
| `datestamp run <folder> --apply` | Perform the renames |
| `datestamp run <folder> --recursive` | Include subfolders as well as the folder itself |
| `datestamp undo <folder>` | Put the previous names back |

`--recursive` combines with `--apply`, and works the same way in a dry run: without `--apply` you get the full list of renames across the whole tree and nothing is touched.

## Photos with no date in their metadata

Not every photo carries a capture date, and `datestamp` will not guess one. Files with no date are left exactly as they are and listed together at the end of the run so that you can see what was passed over:

```
2 skipped (no date in metadata):
  scan-001.jpg
  screenshot.jpg
```

## Two photos, one name

Two photos taken on the same day and sharing a base name would rename to the same thing. Rather than overwrite one with the other, `datestamp` appends a counter to the second and subsequent files: `2026-03-11-beach.jpg`, then `2026-03-11-beach-2.jpg`, then `2026-03-11-beach-3.jpg`. The first file to be processed keeps the plain name.

## Undoing a run

Every applied run writes a file called `.datestamp-log` in the folder, recording the old and new name of each file it renamed. `datestamp undo ./photos` reads that log and restores the original names.

Undo depends on the log, so keep `.datestamp-log` in place if you may want to reverse a run. If the file has been deleted, or the renamed photos have since been moved elsewhere, there is nothing left for `undo` to work from.

## Scope

`datestamp` handles `.jpg` and `.heic` files. Anything else in the folder, including other image formats, is ignored rather than skipped-and-reported: it is not something the tool considers its own.

It also stays in the folder you name. Subfolders are left alone unless you pass `--recursive`.