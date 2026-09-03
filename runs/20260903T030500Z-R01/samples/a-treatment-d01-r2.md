# tug

`tug` pushes a local directory to an S3-compatible bucket. One direction only: local to remote. Nothing on your disk is ever modified, and nothing in the bucket is ever deleted.

## Install

```
go install github.com/example/tug@latest
```

Or download a prebuilt binary from the releases page and put it on your `PATH`.

## Usage

```
tug push [--dry-run] <local-dir> s3://<bucket>/<prefix>
tug status <local-dir> s3://<bucket>/<prefix>
tug verify <local-dir> s3://<bucket>/<prefix>
```

`push` uploads every local file that isn't already on the remote. A file is considered already uploaded when its size and modification time match the remote object; those files are skipped without being read.

`status` reports what `push` would do, without uploading. `push --dry-run` does the same thing and is there for scripting.

`verify` ignores mtimes and compares checksums instead. Use it when you suspect a file changed without its mtime moving, or after copying a tree between machines in a way that reset timestamps.

```
$ tug status ./site s3://my-bucket/site
  upload   index.html          4.1 KiB
  upload   img/header.png      212 KiB
  skip     style.css           (unchanged)
2 to upload, 1 unchanged
```

## Credentials

`tug` looks for `~/.tug/credentials` first:

```ini
[default]
access_key_id = AKIA...
secret_access_key = ...
endpoint = https://s3.us-east-1.amazonaws.com
```

If that file doesn't exist, it falls back to the environment:

```
TUG_ACCESS_KEY_ID
TUG_SECRET_ACCESS_KEY
TUG_ENDPOINT
```

Set the endpoint to point at any S3-compatible service — MinIO, R2, Backblaze B2, and so on.

## Ignoring files

Put a `.tugignore` at the root of the directory you're pushing. It uses gitignore syntax:

```
*.log
node_modules/
!important.log
```

Ignored files are never uploaded and are not reported by `status` or `verify`.

## Limitations

**No delete propagation.** Deleting a local file leaves the remote object in place. If you need the bucket to mirror local deletions, you have to remove the objects yourself.

**No multipart upload.** Files over 5 GB will fail — that's the ceiling for a single-part S3 PUT.

**`verify` is slow on large buckets.** It fetches every object's ETag, one request per object, so runtime grows linearly with object count. On a bucket with tens of thousands of files, expect it to take a while. `status` doesn't have this problem; it uses the listing that comes back from a single paginated call.

---

Two details I had to invent because they weren't in your spec: the exact format of `~/.tug/credentials` (I used AWS-style INI) and the `TUG_*` environment variable names. Swap in whatever the tool actually uses.