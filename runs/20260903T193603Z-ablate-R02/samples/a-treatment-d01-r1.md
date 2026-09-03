# tug

`tug` pushes the contents of a local directory to an S3-compatible bucket. It is one-way: the local tree is the source of truth, and the remote is made to look like it. Files whose size and modification time already match the remote object are skipped, so a second run over an unchanged tree does almost no work.

## Install

With a Go toolchain:

```
go install github.com/example/tug@latest
```

Or download a prebuilt binary for your platform from the releases page and put it somewhere on your `PATH`:

```
curl -sSL https://example.com/tug/latest/tug-linux-amd64 -o /usr/local/bin/tug
chmod +x /usr/local/bin/tug
```

## Quick start

```
tug push ./site s3://my-bucket/site
```

Add `--dry-run` to see the plan without transferring anything:

```
tug push --dry-run ./site s3://my-bucket/site
```

## Commands

`tug push <dir> <s3://bucket/prefix>` uploads every local file that is missing from the remote or whose size or mtime differs. Nothing is deleted remotely, and nothing is ever written locally.

`tug status <dir> <s3://bucket/prefix>` reports what a push would do, grouped into new files, changed files, and skipped files. It is the read-only sibling of `push --dry-run` and takes the same comparison rules.

`tug verify <dir> <s3://bucket/prefix>` compares checksums instead of size and mtime. Use it when you suspect a push was interrupted, when the local clock has moved, or when you need positive evidence that the remote matches the source. It reports mismatches but does not repair them; run `push` afterwards to do that.

## Credentials

`tug` reads credentials from `~/.tug/credentials`, one key per line:

```
access_key_id = AKIA...
secret_access_key = ...
endpoint = https://s3.us-east-1.amazonaws.com
region = us-east-1
```

Environment variables take precedence over the file, which makes them convenient in CI:

- `TUG_ACCESS_KEY_ID`
- `TUG_SECRET_ACCESS_KEY`
- `TUG_ENDPOINT`
- `TUG_REGION`

Set `endpoint` to point at MinIO, Backblaze B2, Cloudflare R2, or any other service that speaks the S3 API.

## Ignoring files

If a `.tugignore` file sits at the root of the directory being pushed, its patterns are applied to every path below it. The syntax is gitignore syntax, including negation with `!` and directory-only patterns ending in `/`:

```
*.tmp
node_modules/
.DS_Store
!keep-this.tmp
```

Ignored paths are never uploaded and never reported as changes.

## Flags

- `--dry-run` prints the actions that would be taken and exits without transferring.
- `--concurrency N` sets the number of parallel uploads (default 8).
- `--verbose` logs every file considered, not only the ones that change.
- `--config PATH` reads credentials from somewhere other than `~/.tug/credentials`.

## Limitations

There is no delete propagation. Removing a file locally leaves the remote object in place, so a bucket that has been pushed to for a long time will accumulate objects that no longer exist in the source. If you need the remote to shrink, delete those objects yourself.

There is no multipart upload. Files larger than 5 GB exceed the single-request limit for S3 PUT and will fail. Split them, or use another tool for those files.

`verify` is slow on large buckets. It fetches the ETag of every object under the prefix, which costs one request per object, so a bucket with hundreds of thousands of objects will take a long time and a noticeable number of API calls. Reach for it when you have a specific reason to distrust mtimes, and rely on `status` the rest of the time.