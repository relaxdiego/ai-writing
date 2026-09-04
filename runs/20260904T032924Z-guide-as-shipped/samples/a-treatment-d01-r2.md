# datestamp

`datestamp` renames photo files so the filename starts with the date the photo was taken, read from the photo's own metadata rather than from the file's timestamp.

```
beach.jpg        ->  2026-03-11-beach.jpg
IMG_0421.heic    ->  2026-03-11-IMG_0421.heic
```

## Install

```
pip install datestamp
```

## Usage

```
datestamp run ./photos
```

By default this changes nothing. It prints the renames it would perform and exits, so you can read the list before committing to it. To perform them, add `--apply`:

```
datestamp run ./photos --apply
```

Only `.jpg` and `.heic` files are considered. Everything else in the folder is left alone, and subfolders are not visited unless you pass `--recursive`.

## Options

- `--apply` — perform the renames instead of printing them.
- `--recursive` — descend into subfolders.

## Photos with no date

A photo whose metadata carries no capture date cannot be renamed, so it is skipped and its name is listed at the end of the run. This happens with images that have been stripped of metadata, exported by some editors, or saved from messaging apps. The skipped list is printed in both the preview and the `--apply` run.

## Name collisions

Two photos taken on the same day and sharing a base name would produce the same new filename. When that happens, a counter is appended to the later ones:

```
2026-03-11-beach.jpg
2026-03-11-beach-2.jpg
2026-03-11-beach-3.jpg
```

## Undo

Each run that renames files writes a `.datestamp-log` in the folder recording the old and new name of every file it touched. To put the names back:

```
datestamp undo ./photos
```

`undo` reads `.datestamp-log` from the folder you give it, so keep that file in place if you may want to reverse the run. Deleting it does not harm the photos, but it does leave the rename unreversible by `datestamp`.