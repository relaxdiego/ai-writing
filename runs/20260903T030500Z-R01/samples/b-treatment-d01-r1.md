# tug

One-way sync from a local directory to an S3-compatible bucket.

`tug` pushes local files up to a bucket and nothing else. It skips files whose size and modification time already match the remote object, so repeated pushes only transfer what changed.

## Install

```
go install github.com/you/tug@latest
```

Or download a prebuilt binary from the releases page and put it on your `PATH`.

## Usage

```
tug push [flags] <local-dir> <bucket>[/prefix]
tug status <local-dir> <bucket>[/prefix]
tug verify <local-dir> <bucket>[/prefix]
```

`push` uploads everything that differs. `status` reports what a push would do without touching the network beyond a listing. `verify` compares checksums instead of size and mtime, which catches files that were modified in place without their mtime changing.

Add `--dry-run` to `push` to print the planned uploads and exit.

```
tug push ./site my-bucket/assets --dry-run
tug push ./site my-bucket/assets
tug status ./site my-bucket/assets
```

## Credentials

`tug` reads `~/.tug/credentials`:

```ini
[default]
access_key_id = AKIA...
secret_access_key = ...
endpoint = https://s3.example.com
region = us-east-1
```

Environment variables take precedence: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_ENDPOINT_URL`, `AWS_REGION`.

## Ignoring files

Drop a `.tugignore` in the root of the local directory. It uses gitignore syntax:

```
*.log
build/
!build/index.html
```

## Limitations

- **No delete propagation.** Removing a file locally leaves the remote object in place. Clean up deletions yourself.
- **No multipart upload.** Files over 5 GB will fail; the S3 API requires multipart above that size.
- **`verify` is slow on large buckets.** It fetches the ETag for every object, one request each. Use it on a prefix rather than a whole bucket when you can.