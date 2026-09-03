# datestamp

`datestamp` renames photo files so that each filename starts with the date the photo was taken, read from the photo's own metadata. A file called `beach.jpg` shot on 11 March 2026 becomes `2026-03-11-beach.jpg`, so that a plain alphabetical listing of the folder is also a chronological one.

## Install

```
pip install datestamp
```

## Usage

Point the `run` command at a folder:

```
datestamp run ./photos
```

By default this changes nothing. It prints the renames it would make and exits, so you can read the list before committing to it. When the list looks right, repeat the command with `--apply`:

```
datestamp run ./photos --apply
```

The flags and commands are:

- `run <folder>` — show the renames for a folder; add `--apply` to perform them.
- `undo <folder>` — restore the previous names, as described below.
- `--apply` — actually rename the files instead of printing what would happen.
- `--recursive` — descend into subfolders; without it, only the named folder is read.

## What happens to awkward files

A photo whose metadata carries no date is left alone. Rather than guessing from the file's modification time, which is often the date it was copied rather than the date it was taken, `datestamp` skips the file and collects it in a list printed at the end of the run, so you can see at a glance which images need attention.

Two photos in the same folder can easily want the same name, since a burst of shots on one day shares both the date and the original filename stem. When that happens the second file gets a `-2` suffix and the third a `-3`, counting up as far as needed: `2026-03-11-beach.jpg`, `2026-03-11-beach-2.jpg`, and so on.

Only `.jpg` and `.heic` files are considered. Anything else in the folder is passed over without comment, so a folder of photos mixed with videos, sidecar files or notes can be handled safely.

## Undoing a run

Every applied run writes a file called `.datestamp-log` in the folder, recording the old and new name of each file it touched. The `undo` command reads that log and puts the names back:

```
datestamp undo ./photos
```

Because the log lives in the folder alongside the photos, it travels with them if you move or copy the folder, and an undo works as long as the log is still there. Deleting `.datestamp-log` makes the renames permanent in the sense that `datestamp` can no longer reverse them.