Here's a README for `datestamp`:

---

# datestamp

Renames photo files so the filename starts with the date the photo was taken, read from the photo's own metadata.

```
IMG_4821.jpg  ->  2026-03-11-beach.jpg
```

## Install

```
pip install datestamp
```

## Usage

Point it at a folder of photos:

```
datestamp run ./photos
```

By default this is a **dry run**: it prints the renames it would make and changes nothing. When the output looks right, add `--apply`:

```
datestamp run ./photos --apply
```

## What it does

**Naming.** Each file gets its capture date prepended in `YYYY-MM-DD` form, followed by the original name — `beach.jpg` taken on 11 March 2026 becomes `2026-03-11-beach.jpg`.

**Photos with no date.** If a photo's metadata has no capture date, it is left alone and listed at the end of the run so you know what was skipped.

**Name collisions.** If two photos would end up with the same name, a counter is appended: `2026-03-11-beach.jpg`, `2026-03-11-beach-2.jpg`, `2026-03-11-beach-3.jpg`.

**Log file.** Every applied rename is recorded in a `.datestamp-log` file in the folder, holding the old and new name of each file.

## Undo

```
datestamp undo ./photos
```

This reads `.datestamp-log` in that folder and puts the original names back. If the log file is gone, the renames can't be undone.

## Options

| Option | Effect |
| --- | --- |
| `--apply` | Perform the renames. Without it, `run` only prints what it would do. |
| `--recursive` | Also process subfolders. By default only the folder you name is processed. |

## Limitations

- Only `.jpg` and `.heic` files are handled. Other files in the folder are ignored.
- Subfolders are skipped unless you pass `--recursive`.
- Undo depends on `.datestamp-log`; don't delete it if you may want to reverse a run.

---

I've left this in the chat rather than writing it to disk, since the working directory is an unrelated scratch repo — tell me where you'd like it saved and I'll drop it there.