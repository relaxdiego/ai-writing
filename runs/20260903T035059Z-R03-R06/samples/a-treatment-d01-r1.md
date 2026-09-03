Below is the README. I've filled in a placeholder module path (`github.com/example/tug`) and a credentials-file layout, since neither was specified.

````markdown
# tug

tug pushes a local directory to an S3-compatible bucket. It is one-way by
design: the local tree is the source of truth, and nothing on the remote is ever
copied back down. Before uploading a file, tug compares its size and
modification time against the matching remote object and skips it if both agree,
so a second run over an unchanged tree does little beyond listing the bucket.

## Install

With a Go toolchain:

```
go install github.com/example/tug@latest
```

Otherwise, download the archive for your platform from the releases page,
extract it, and put the `tug` binary somewhere on your `PATH`. The binary is
static and has no runtime dependencies.

## Commands

`tug push [dir]` walks `dir` (the current directory if omitted), compares each
file against the bucket, and uploads the ones that differ. Passing `--dry-run`
runs the same comparison and prints the upload plan without transferring
anything, which is the safe way to try a new configuration.

`tug status [dir]` performs the comparison and reports it without ever writing:
new files, changed files, and a count of everything skipped. It overlaps with
`push --dry-run` and exists so that the read-only check is the shorter thing to
type.

`tug verify [dir]` checks contents rather than metadata. It reads each local
file, computes its checksum, and compares that against the remote object's ETag,
which catches the case where a file was rewritten with the same size and the
same timestamp. Use it when you want to be sure a push landed correctly rather
than when you want to know what to push next.

## Credentials

tug reads `~/.tug/credentials`, an INI file with one section per profile:

```ini
[default]
access_key_id = AKIAEXAMPLE
secret_access_key = wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
endpoint = https://s3.example.com
region = us-east-1
bucket = my-bucket
```

Select a profile other than `default` with `--profile`. Each field can also be
supplied through the environment as `TUG_ACCESS_KEY_ID`,
`TUG_SECRET_ACCESS_KEY`, `TUG_ENDPOINT`, `TUG_REGION`, and `TUG_BUCKET`;
environment variables override the file field by field, so you can keep a
profile on disk and point it at a different bucket for one run.

## Ignoring files

If a `.tugignore` file exists at the root of the directory being pushed, tug
reads it as gitignore syntax: one glob per line, `#` for comments, a leading `!`
to re-include a previously excluded path, and a trailing `/` to match
directories only. Ignored paths are excluded from uploads and from the output of
`status` and `verify`, so they will not show up as drift.

## Limitations

- No delete propagation. Removing a file locally leaves its object in the
  bucket, and tug will not tell you about it. Prune the remote yourself.
- No multipart upload. Every object is sent as a single PUT, so files larger
  than 5GB are rejected by the service and the push fails on that file.
- `verify` fetches the ETag of every object in the bucket, one request each.
  On a bucket with many thousands of objects this takes minutes and costs a
  request per object, so it is worth scoping to a subdirectory.
````