# datestamp

`datestamp` renames photo files so the filename starts with the date the photo was taken, read from the photo's own metadata rather than from the file's timestamp on disk. A picture called `beach.jpg` shot on 11 March 2026 becomes `2026-03-11-beach.jpg`, so a folder sorted by name is a folder sorted by date.

## Install

```
pip install datestamp
```

## Usage

Point it at a folder:

```
datestamp run ./photos
```

That is a preview. It prints every rename it would make and changes nothing on disk, so you can read the list first and satisfy yourself that the dates it found are the dates you expect. When the preview looks right, run it again with `--apply` to carry the renames out:

```
datestamp run ./photos --apply
```

`datestamp` looks at `.jpg` and `.heic` files, and only at the ones sitting directly in the folder you name. Add `--recursive` to descend into subfolders as well.

## Photos with no date

A file whose metadata carries no capture date is left alone. Rather than guessing from the modification time or the name, `datestamp` skips it and collects every skipped file into a list printed at the end of the run, so what was missed is visible while you are still looking at the output.

## Name collisions

If two photos would end up with the same new name, the first keeps it and the rest get a counter before the extension:

```
2026-03-11-beach.jpg
2026-03-11-beach-2.jpg
2026-03-11-beach-3.jpg
```

Nothing is overwritten.

## Undoing a run

Each applied run writes a file called `.datestamp-log` in the folder, recording the old and new name of everything it touched. To put the names back:

```
datestamp undo ./photos
```

The undo reads that log, so it depends on the log still being there. If you delete or move `.datestamp-log`, the renames stand and there is no record left to reverse them from.