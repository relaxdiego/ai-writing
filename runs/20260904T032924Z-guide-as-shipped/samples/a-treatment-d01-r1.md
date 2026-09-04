# datestamp

Renames photo files so the filename starts with the date the photo was taken, read from the photo's own metadata. A photo called `beach.jpg` shot on 11 March 2026 becomes `2026-03-11-beach.jpg`, so sorting the folder by name puts it in the order the pictures were taken.

## Install

```
pip install datestamp
```

## Use

Point it at a folder:

```
datestamp run ./photos
```

By default this changes nothing. It prints the rename it would make for each file and stops there, so you can read the list before committing to it. Run it again with `--apply` to perform the renames:

```
datestamp run ./photos --apply
```

A dry run looks like this:

```
$ datestamp run ./photos
beach.jpg          -> 2026-03-11-beach.jpg
IMG_0042.heic      -> 2026-03-11-IMG_0042.heic
sunset.jpg         -> 2026-03-12-sunset.jpg

skipped (no date in metadata):
  scan001.jpg
```

### Options

- `--apply` — carry out the renames instead of printing them.
- `--recursive` — descend into subfolders. Without it, only the files directly inside the given folder are considered.

## What it does with awkward files

A photo whose metadata carries no date is left alone. Those files are listed together at the end of the run so you can see what was passed over rather than having to compare the folder before and after.

When two photos would end up with the same name, the second one gets a counter before the extension: `2026-03-11-beach.jpg` and then `2026-03-11-beach-2.jpg`, `-3`, and so on. No existing file is overwritten to make room for a new name.

## Undoing a run

Every applied run appends to a file called `.datestamp-log` in the folder it worked on, recording the old and new name of each file it touched. To put the names back:

```
datestamp undo ./photos
```

`undo` works entirely from that log, so keep it with the folder. If the log has been deleted or the folder has been moved without it, there is no record left to restore from.

## Scope

`datestamp` handles `.jpg` and `.heic` files. Anything else in the folder is ignored, including video, RAW files and sidecar metadata.