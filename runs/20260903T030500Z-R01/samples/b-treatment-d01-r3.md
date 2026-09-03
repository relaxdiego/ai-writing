# tug

One-way sync from a local directory to an S3-compatible bucket.

`tug` pushes local files up to a bucket and leaves everything else alone. Files whose size and modification time already match the remote object are skipped, so repeated pushes only move what changed.

## Install

```sh
go install github.com/you/tug@latest
```

Or download a prebuilt binary from the releases page and put it on your `PATH`.

## Credentials

`tug` reads credentials from `~/.tug/credentials`:

```ini
[default]
access_key_id = AKIA...
secret_access_key = ...
endpoint = https://s3.example.com
region = us-east-1
```

Environment variables override the file:

```sh
export TUG_ACCESS_KEY_ID=AKIA...
export TUG_SECRET_ACCESS_KEY=...
export TUG_ENDPOINT=https://s3.example.com
export TUG_REGION=us-east-1
```

## Usage

```sh
tug push   ./site s3://my-bucket/prefix
tug status ./site s3://my-bucket/prefix
tug verify ./site s3://my-bucket/prefix
```

- **`push`** uploads every local file that is missing remotely or whose size or mtime differs.
- **`status`** reports what a push would do without contacting the write path at all.
- **`verify`** compares checksums instead of mtimes, so it catches corruption and silent divergence that `status` misses.

Add `--dry-run` to `push` to print the planned uploads and exit without writing anything:

```sh
tug push --dry-run ./site s3://my-bucket/prefix
```

## Ignoring files

Put a `.tugignore` in the root of the local directory. It uses gitignore syntax:

```
node_modules/
*.log
!important.log
.DS_Store
```

## Limitations

- **No delete propagation.** Removing a file locally does not remove it from the bucket. Deletions have to be done by hand or with another tool.
- **No multipart upload.** Files larger than 5 GB will fail to upload.
- **`verify` is slow on large buckets.** It fetches the ETag for every object, which means one request per object. Expect it to take a while past a few thousand keys; use `status` for routine checks and save `verify` for when you actually suspect drift.