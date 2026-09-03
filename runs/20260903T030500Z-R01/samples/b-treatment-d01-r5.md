# tug

One-way sync from a local directory to an S3-compatible bucket.

`tug` pushes local files up to a bucket and skips anything whose size and modification time already match the remote object. It never pulls, and it never deletes.

## Install

```
go install github.com/you/tug@latest
```

Or download a prebuilt binary from the releases page and put it on your `PATH`.

## Credentials

`tug` reads `~/.tug/credentials`:

```ini
[default]
endpoint   = https://s3.example.com
region     = us-east-1
access_key = AKIAEXAMPLE
secret_key = wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
```

Environment variables override the file:

```
TUG_ENDPOINT
TUG_REGION
TUG_ACCESS_KEY
TUG_SECRET_KEY
```

## Usage

```
tug push   [--dry-run] <local-dir> s3://bucket/prefix
tug status <local-dir> s3://bucket/prefix
tug verify <local-dir> s3://bucket/prefix
```

**`push`** uploads every local file that is missing remotely or whose size or mtime differs. With `--dry-run` it prints the same plan without transferring anything.

**`status`** reports what a push would do, without uploading. It uses the same size-and-mtime comparison as `push`.

**`verify`** compares checksums instead of mtimes. Use it when you suspect a file changed without its mtime moving, or after restoring from a backup that reset timestamps.

```
$ tug push ./site s3://assets/site --dry-run
+ css/main.css      12.4 KB   (new)
~ index.html         3.1 KB   (size differs)
  img/logo.png                (skipped, up to date)

2 to upload, 1 unchanged
```

## Ignoring files

Put a `.tugignore` at the root of the local directory. It uses gitignore syntax:

```
*.tmp
node_modules/
!keep-this.tmp
```

## Limitations

- **No delete propagation.** Files removed locally stay in the bucket. Clean those up yourself.
- **No multipart upload.** Files over 5 GB will fail to upload.
- **`verify` is slow on large buckets.** It fetches every object's ETag, one request per object.