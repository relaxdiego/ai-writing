# tug

`tug` pushes a local directory to an S3-compatible bucket. It is one-way by design: the local tree is the source of truth, and nothing on the remote is ever copied back down. On each run it compares each local file against the size and modification time of the corresponding remote object and uploads only what differs, so a second push over an unchanged tree costs little beyond the bucket listing.

## Installation

With a Go toolchain:

```
go install github.com/you/tug@latest
```

Or download a prebuilt binary for your platform from the releases page, make it executable, and put it somewhere on your `PATH`:

```
curl -Lo tug https://github.com/you/tug/releases/latest/download/tug-linux-amd64
chmod +x tug && sudo mv tug /usr/local/bin/
```

## Credentials

`tug` looks for `~/.tug/credentials` first. The file is a simple key/value list, and it should not be world-readable:

```
access_key_id = AKIAEXAMPLE
secret_access_key = wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
endpoint = https://s3.us-east-1.amazonaws.com
region = us-east-1
```

If that file is missing, `tug` falls back to the environment: `TUG_ACCESS_KEY_ID`, `TUG_SECRET_ACCESS_KEY`, `TUG_ENDPOINT` and `TUG_REGION`. Environment variables are the better fit for CI, where writing a credentials file to disk buys you nothing.

## Usage

Every command takes a local directory and a bucket destination, and every command accepts `--dry-run`, which prints the work that would be done and exits without touching the remote. Getting into the habit of a dry run first is worth the extra keystrokes, since a mistyped source path is otherwise indistinguishable from a large legitimate upload until it is finished.

```
tug push   ./site  s3://my-bucket/prefix
tug status ./site  s3://my-bucket/prefix
tug verify ./site  s3://my-bucket/prefix
```

`tug push` uploads every local file whose size or mtime differs from the remote object, and every file that has no remote object at all. Files that match on both attributes are skipped without being read.

`tug status` performs the same comparison and reports what a push would do, but never uploads. It is the read-only sibling of `push --dry-run` and is safe to wire into a prompt or a monitoring check.

`tug verify` ignores mtimes and compares checksums instead, which catches the cases mtime comparison cannot: a file whose contents changed while its size and timestamp were preserved, or an upload that was truncated or corrupted in transit. Use it after a migration or when you have reason to distrust a previous push, rather than on every run.

## Ignoring files

If a `.tugignore` file is present at the root of the local directory, `tug` reads it using gitignore syntax, including negation with `!` and directory-only patterns with a trailing slash:

```
*.log
node_modules/
.DS_Store
!important.log
```

Ignored paths are excluded from all three commands, so a file you ignore will not be uploaded by `push`, will not appear in `status`, and will not be checked by `verify`.

## Limitations

There is no delete propagation. Removing a file locally leaves the remote object in place, and the only way to clear it is to delete it yourself through your provider's console or CLI. Anything using `tug` as a mirror rather than an append-only push should account for that.

Files larger than 5GB will fail, because `tug` does not yet implement multipart upload and a single PUT is capped at that size by the S3 API. The error is reported per file and does not abort the rest of the run.

`verify` is slow on large buckets. It fetches the ETag of every object rather than working from a listing, which means one request per file and a runtime that scales linearly with object count. On a bucket of any real size, expect to run it deliberately rather than on a schedule.

---

I filled in a few specifics the brief did not pin down: the credentials file format and key names, the environment variable names, the module path in the `go install` line, and the argument shape (`tug push <local-dir> <s3-uri>`). Correct any of those and I will update the text.