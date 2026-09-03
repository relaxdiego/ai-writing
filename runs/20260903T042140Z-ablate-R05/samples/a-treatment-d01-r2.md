# tug

`tug` pushes a local directory into an S3-compatible bucket. It is one-way by design: files travel from local to remote and never the other direction, so a sync can never overwrite or delete anything on your disk. On each run it compares every local file against the matching remote object and uploads only the ones whose size or modification time differs, which keeps repeat pushes over a mostly unchanged tree fast and cheap.

## Installation

With a Go toolchain installed:

```
go install github.com/example/tug@latest
```

Prebuilt binaries for Linux, macOS and Windows are attached to each release. Download the archive for your platform, extract it, and put the `tug` binary somewhere on your `PATH`.

## Usage

All three commands take a local directory and a bucket, optionally with a key prefix:

```
tug push ./public my-bucket/assets
```

### `tug push`

Uploads every local file that is missing from the bucket or whose size or mtime differs from the remote object. Files that match on both are skipped without being read. Pass `--dry-run` to print the same upload plan without transferring anything, which is the safe way to check a new prefix or a freshly written `.tugignore` before committing to it.

### `tug status`

Compares the local tree against the bucket and prints a summary of what differs: files that are new locally, files that have changed, and files present remotely with no local counterpart. Nothing is uploaded. Where `push --dry-run` shows you the work a push would do, `status` is meant for a quick look at how far the two sides have drifted.

### `tug verify`

Compares checksums instead of size and mtime. This catches the cases the ordinary comparison cannot see, such as a file whose contents changed while its mtime was preserved, or an upload that completed but landed corrupted. Because it is a stricter and much slower check, `verify` is best run occasionally rather than as part of every push.

## Credentials

`tug` looks for credentials in `~/.tug/credentials`, which uses a simple profile format:

```
[default]
access_key_id = AKIAEXAMPLE
secret_access_key = wJalrXUtnFEMI/EXAMPLEKEY
endpoint = https://s3.example.com
region = us-east-1
```

The environment variables `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_ENDPOINT_URL` and `AWS_REGION` are also read, and take precedence over the file when both are present. That ordering makes it easy to keep a default profile on your workstation and override it in CI without touching the file.

## Ignoring files

If a `.tugignore` file exists at the root of the directory being pushed, `tug` reads it using gitignore syntax: one pattern per line, `#` for comments, `!` to negate an earlier pattern, and a trailing `/` to match directories only. Ignored files are excluded from all three commands, so a file skipped by `push` will not be reported by `status` or checked by `verify`.

```
node_modules/
*.log
.DS_Store
!important.log
```

## Known limitations

There is no delete propagation. Removing a file locally leaves the remote object in place, and you will need to delete it yourself with another tool. `status` will report such objects as remote-only, so at least you can see what has accumulated.

Files larger than 5 GB cannot be uploaded, because `tug` does not yet implement multipart upload. A push that encounters one will report the file as too large and continue with the rest of the tree.

`verify` is slow on large buckets. It fetches the ETag of every object it checks, which means one request per file and no way to batch them, so a bucket with tens of thousands of objects can take a long time to work through. Scoping it to a prefix rather than the whole bucket is usually the practical workaround.

---

Two details were not in your description and I filled them in: the credentials file format (an INI-style `[default]` profile) and the environment variable names (the conventional `AWS_*` ones, taking precedence over the file). Tell me the real names and I will correct them. I also left the `go install` path as `github.com/example/tug`.