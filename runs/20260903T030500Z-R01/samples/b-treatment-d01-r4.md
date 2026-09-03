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

## Commands

### `tug push`

Uploads everything in the local directory that differs from the remote bucket.

```
tug push ./site s3://my-bucket/prefix
tug push ./site s3://my-bucket/prefix --dry-run
```

A file is uploaded if it does not exist remotely, or if its size or mtime differs from the remote object. `--dry-run` prints the same plan without transferring anything.

### `tug status`

Shows what a push would do, without the transfer and without the exit-code semantics of a real run.

```
tug status ./site s3://my-bucket/prefix
```

### `tug verify`

Compares local and remote checksums instead of size and mtime. Use it when you suspect an interrupted upload or a file that was modified without its mtime changing.

```
tug verify ./site s3://my-bucket/prefix
```

## `.tugignore`

Put a `.tugignore` in the root of the directory you are pushing. It uses gitignore syntax:

```
*.log
node_modules/
!important.log
```

## Limitations

- **No delete propagation.** Files removed locally stay in the bucket. Clean up remote objects yourself.
- **No multipart upload.** Files over 5GB will fail to upload.
- **`verify` is slow on large buckets.** It fetches the ETag for every object, one request each, so a bucket with hundreds of thousands of objects will take a while.