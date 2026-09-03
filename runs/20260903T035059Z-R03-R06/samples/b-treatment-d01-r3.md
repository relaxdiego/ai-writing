# tug

`tug` pushes a local directory to an S3-compatible bucket. It is one-way only: local state is the source of truth, and nothing on the remote is ever copied back down. Files are skipped when their size and modification time already match the remote object, so a repeat push over an unchanged tree costs a listing and little else.

## Install

With a Go toolchain:

```
go install github.com/you/tug@latest
```

Otherwise download a prebuilt binary from the releases page, and put it somewhere on your `PATH`:

```
curl -L https://github.com/you/tug/releases/latest/download/tug_linux_amd64 -o tug
chmod +x tug && sudo mv tug /usr/local/bin/
```

## Quick start

```
tug push ./site s3://my-bucket/site
```

Add `--dry-run` to see the plan without transferring anything. The output lists each file `tug` would upload and each one it would skip, which is the fastest way to check that your `.tugignore` matches what you think it does.

## Commands

`tug push <dir> <s3-url>` walks the local directory, compares each file against the corresponding remote object, and uploads whatever differs. Comparison is by size and mtime; a file whose contents changed without its mtime moving will not be detected here, which is what `verify` is for.

`tug status <dir> <s3-url>` performs the same comparison and prints the result without uploading. It is equivalent to `push --dry-run` and exists so that scripts can check for drift without the word "push" in them.

`tug verify <dir> <s3-url>` compares checksums instead of mtimes, fetching each object's ETag from the remote and checking it against the local file's MD5. Use it after a push you have reason to distrust, or on a schedule to catch silent corruption. It is much slower than `status`; see the limitations below.

## Credentials

`tug` reads credentials from `~/.tug/credentials`, an INI file with an optional profile name selected by `--profile`:

```ini
[default]
access_key_id = AKIA...
secret_access_key = ...
endpoint = https://s3.us-west-2.amazonaws.com
region = us-west-2
```

Environment variables take precedence over the file, so CI runs can supply secrets without writing them to disk: `TUG_ACCESS_KEY_ID`, `TUG_SECRET_ACCESS_KEY`, `TUG_ENDPOINT` and `TUG_REGION`. The `endpoint` setting is what makes non-AWS providers work; point it at MinIO, R2, Backblaze B2 or anything else that speaks the S3 API.

## Ignoring files

If a `.tugignore` file exists at the root of the directory being pushed, `tug` reads it using gitignore syntax: one pattern per line, `#` for comments, `!` to negate an earlier pattern, and a trailing `/` to match directories only.

```
node_modules/
*.log
.DS_Store
!important.log
```

Only the root-level `.tugignore` is consulted. Nested ignore files in subdirectories are not read.

## Limitations

There is no delete propagation. Removing a file locally leaves the remote object in place, and cleaning up stale objects is a manual job. This is deliberate for now, since a bug in deletion logic is considerably more expensive than a bug in upload logic.

Files larger than 5GB will fail, because `tug` does not implement multipart upload and 5GB is the single-request ceiling in the S3 API. Split such files or use another tool for them.

`verify` is slow on large buckets. It issues a request per object to fetch the ETag, so runtime grows linearly with object count and is dominated by round-trip latency rather than bandwidth. On a bucket with hundreds of thousands of objects, expect it to take a long time and to cost a corresponding number of API calls. Checksums for multipart-uploaded objects created by other tools will not match a plain MD5 either, so `verify` reports those as mismatches even when the data is intact.