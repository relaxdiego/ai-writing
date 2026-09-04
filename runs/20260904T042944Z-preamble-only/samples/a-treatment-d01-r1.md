# datestamp

`datestamp` renames photo files so the filename starts with the date the photo was taken, read from the photo's own metadata. A picture called `beach.jpg` taken on 11 March 2026 becomes `2026-03-11-beach.jpg`, so that sorting a folder by name sorts it by date.

## Install

```
pip install datestamp
```

## Usage

Point it at a folder:

```
datestamp run ./photos
```

By default this is a dry run. It prints the rename it would perform for each photo and changes nothing on disk, so you can read the list before committing to it. When the list looks right, repeat the command with `--apply` to perform the renames:

```
datestamp run ./photos --apply
```

Only the folder you name is examined. Add `--recursive` to descend into subfolders as well.

## What it does to each file

`datestamp` reads `.jpg` and `.heic` files and leaves everything else in the folder untouched. Three cases are worth knowing about before you run it with `--apply`:

- A photo whose metadata carries no date cannot be renamed, so it is skipped and its name is printed in a list at the end of the run.
- Where two photos would end up with the same name, the second and subsequent files get a counter before the extension: `2026-03-11-beach.jpg`, `2026-03-11-beach-2.jpg`, `2026-03-11-beach-3.jpg`.
- A file already renamed by a previous run is renamed again from its metadata, which means running `datestamp` twice over the same folder is safe.

## Undoing a run

Every applied run writes the old and new name of each file to `.datestamp-log` in the folder. To put the original names back:

```
datestamp undo ./photos
```

The undo reads that log, so it only works while the log is still in the folder. If you delete `.datestamp-log`, or move the renamed photos somewhere else, the original names are gone and `datestamp` cannot recover them.