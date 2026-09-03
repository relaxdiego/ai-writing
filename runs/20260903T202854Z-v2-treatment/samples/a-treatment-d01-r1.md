# datestamp

Renames photo files so the filename begins with the date the photo was taken: `beach.jpg` becomes `2026-03-11-beach.jpg`. The date is read from the photo's own metadata, so it survives the copying and syncing that overwrite a file's creation and modification times, and sorting the folder by name sorts it by date.

## Install

```
pip install datestamp
```

## Renaming a folder

```
datestamp run ./photos
```

By default this only reports. It prints the renames it would make and changes nothing on disk, so you can read the list first and check that the dates are what you expect. When the list looks right, run the same command again with `--apply` to carry the renames out:

```
datestamp run ./photos --apply
```

Only `.jpg` and `.heic` files are considered; anything else in the folder is left alone. `run` looks at the folder you name and no deeper, so a folder of subfolders needs `--recursive`:

```
datestamp run ./photos --recursive --apply
```

## Photos without a date, and photos that collide

Not every file carries a usable date. A photo whose metadata has none is skipped rather than guessed at, left under its original name, and listed together with the others at the end of the run so you can deal with them by hand.

Where two photos would end up with the same new name, the first keeps it and the rest get a counter:

```
2026-03-11-beach.jpg
2026-03-11-beach-2.jpg
2026-03-11-beach-3.jpg
```

## Undoing a run

Every applied run writes the old and new name of each file it touched to `.datestamp-log`, kept in the folder it worked on. To put the original names back:

```
datestamp undo ./photos
```

The log is what makes this possible, so leave it where it is. If it is deleted or the folder is moved without it, `undo` has nothing to read and the previous names are gone.

## Summary of the commands

| Command | Effect |
| --- | --- |
| `datestamp run DIR` | Print the renames that would be made; change nothing |
| `datestamp run DIR --apply` | Perform the renames and write `.datestamp-log` |
| `datestamp run DIR --recursive` | Include subfolders (combines with `--apply`) |
| `datestamp undo DIR` | Restore the names recorded in `.datestamp-log` |