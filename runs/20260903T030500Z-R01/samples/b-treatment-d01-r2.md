# tug

One-way sync from a local directory to an S3-compatible bucket.

`tug` pushes local files up to a bucket. It never pulls, and it never deletes. Files whose size and modification time match the remote object are skipped, so repeat runs over a large tree are cheap.

## Install

```
go install github.com/you/tug@latest
```

Or download a prebuilt binary from the releases page and put it on your `PATH`.

## Credentials

`tug` reads credentials from `~/.tug/credentials`:

```ini
[default]
access_key_id     = AKIA...
secret_access_key = ...
endpoint          = https://s3.example.com
region            = us-east-1
```

Environment variables take precedence if set:

```
AWS_ACCESS_KEY_ID
AWS_SECRET_ACCESS_KEY
AWS_ENDPOINT_URL
AWS_REGION
```

## Commands

**`tug push <dir> s3://bucket/prefix`** — uploads everything under `<dir>` that isn't already present with a matching size and mtime.

**`tug status <dir> s3://bucket/prefix`** — lists what a push would do, without doing it. Read-only.

**`tug verify <dir> s3://bucket/prefix`** — compares local checksums against remote ETags instead of trusting mtimes. Use this when you suspect a partial or corrupted upload.

`--dry-run` works on `push` and prints the same plan `status` would, in the context of the flags you passed.

## Ignoring files

Drop a `.tugignore` in the root of the directory you're syncing. It uses gitignore syntax:

```
*.log
node_modules/
.DS_Store
!important.log
```

## Example

```
$ tug status ./site s3://my-bucket/site
  upload  index.html      (new)
  upload  assets/app.js   (modified)
  skip    assets/logo.png
2 to upload, 1 unchanged

$ tug push ./site s3://my-bucket/site
uploaded 2 files (48 KiB) in 1.2s
```

## Limitations

- **No delete propagation.** Removing a file locally leaves the remote object in place. You have to delete it yourself.
- **No multipart upload.** Files over 5 GB will fail; that's the single-request ceiling on most S3 implementations.
- **`verify` is slow on large buckets.** It fetches every object's ETag one at a time, so runtime scales with object count. It's a diagnostic tool, not something to put in a loop.