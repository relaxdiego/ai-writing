# datestamp

Renames photo files so the name begins with the date the photo was taken, read from the photo's own metadata. `beach.jpg` taken on 11 March 2026 becomes `2026-03-11-beach.jpg`, so sorting the folder by name sorts it by date.

## Install

```
pip install datestamp
```

## Usage

```
datestamp run ./photos
```

This prints the renames it would make and changes nothing on disk. Nothing is renamed until you ask for it explicitly:

```
datestamp run ./photos --apply
```

Read the dry run, then repeat the same command with `--apply` when the listing looks right.

## What happens to the names

The date is added as a prefix and the rest of the original name is kept, so `beach.jpg` becomes `2026-03-11-beach.jpg` and you can still tell your files apart afterwards.

If two photos would end up with the same name, a counter is appended to the later ones:

```
2026-03-11-beach.jpg
2026-03-11-beach-2.jpg
2026-03-11-beach-3.jpg
```

## Photos with no date

A photo whose metadata has no date cannot be renamed, so it is left exactly as it is. Every skipped file is listed at the end of the run, dry or applied, so you can see what was passed over rather than having to compare the folder before and after.

## Undoing a run

Each applied run writes a file called `.datestamp-log` in the folder, recording the old and new name of everything it renamed. To reverse it:

```
datestamp undo ./photos
```

`undo` reads that log and puts the old names back. The log lives in the folder it describes, so keep it there: if it is deleted, or the photos are moved elsewhere, there is nothing left for `undo` to read.

## What it covers

Only `.jpg` and `.heic` files are considered. Anything else in the folder is left alone and not renamed.

Subfolders are not visited by default. Pass `--recursive` to descend into them:

```
datestamp run ./photos --recursive
```

## Options

- `run <folder>` — list the renames for a folder; add `--apply` to carry them out
- `undo <folder>` — restore the names recorded in that folder's `.datestamp-log`
- `--apply` — perform the renames instead of only printing them
- `--recursive` — include subfolders