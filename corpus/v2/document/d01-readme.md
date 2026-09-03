---
id: d01
register: document
name: README for a small tool
---
Write a README for the following tool.

The tool is called `datestamp`. It renames photo files so the filename starts with the date the photo was taken, read from the photo's own metadata, for example `2026-03-11-beach.jpg`. It is installed with `pip install datestamp`. You run it as `datestamp run ./photos`. By default it prints what it would rename and changes nothing; `--apply` performs the renames. If a photo has no date in its metadata it is skipped and listed at the end. If two photos would end up with the same name, a counter is added (`-2`, `-3`). It keeps a file called `.datestamp-log` in the folder recording the old and new names, and `datestamp undo ./photos` reads that file and puts the names back. It only handles `.jpg` and `.heic`. It does not recurse into subfolders unless given `--recursive`.
