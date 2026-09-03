# tug

`tug` pushes a local directory to an S3-compatible bucket. It is deliberately one-way: local is the source of truth, the bucket is a destination, and nothing about the remote ever changes what is on your disk. If you have been reaching for `rclone` or `aws s3 sync` and using perhaps a tenth of what they offer, `tug` is the tenth.

## Install

With a Go toolchain:

```
go install github.com/yourorg/tug@latest
```

Or download a prebuilt binary from the releases page, drop it on your `PATH`, and confirm it runs:

```
tug --version
```

## Credentials

`tug` looks for credentials in `~/.tug/credentials` first, falling back to the environment. The file is INI-style, with a `default` profile:

```ini
[default]
access_key_id = AKIAEXAMPLE
secret_access_key = wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
endpoint = https://s3.us-east-1.amazonaws.com
region = us-east-1
```

The equivalent environment variables are `TUG_ACCESS_KEY_ID`, `TUG_SECRET_ACCESS_KEY`, `TUG_ENDPOINT`, and `TUG_REGION`. Because the endpoint is explicit rather than derived from a region, any S3-compatible service works the same way — MinIO, Backblaze B2, Cloudflare R2, Ceph — and switching between them is a matter of changing one line.

## Usage

The three commands share the same argument shape: a local directory and a bucket destination, written as `s3://bucket/optional/prefix`.

```
tug push ./site s3://my-bucket/assets
tug status ./site s3://my-bucket/assets
tug verify ./site s3://my-bucket/assets
```

`push` uploads everything that differs. Before sending a file, `tug` compares its size and modification time against the remote object's metadata, and skips the upload when both match; on a directory that has barely changed since the last run, almost everything is skipped and the push finishes in the time it takes to list the bucket. Pass `--dry-run` to print exactly what would be uploaded without touching the remote, which is worth doing the first time you point `tug` at an unfamiliar bucket.

`status` performs that same comparison and reports the result without uploading anything. Think of it as `push --dry-run` with a summary rather than a transfer log.

`verify` answers a different and more paranoid question: not "does this look current?" but "is the byte content actually identical?" It computes a checksum for each local file and compares it against the remote object's ETag, which catches the cases mtime comparison cannot — a file restored from backup with a fresh timestamp, an upload that was truncated mid-flight, a bucket someone else has been writing to. Run it after a migration or when a push behaved strangely, rather than as part of your regular loop.

## Ignoring files

Drop a `.tugignore` in the root of the directory you are pushing. It uses gitignore syntax, including negation with `!` and directory-scoped patterns, so most of the time you can copy the relevant lines out of your `.gitignore`:

```
node_modules/
*.log
.DS_Store
!important.log
```

## Limitations

These are known and intentional in the sense that `tug` chooses not to solve them, so decide whether they matter to you before adopting it.

There is **no delete propagation**. Removing a file locally leaves the corresponding object in the bucket forever, and over a long enough life the remote accumulates every file the directory has ever contained. If you need the remote to be an exact mirror, `tug` is the wrong tool.

There is **no multipart upload**, so any single file over 5GB will fail. The workaround is to split or exclude such files; there is no flag that makes them work.

**`verify` is slow on large buckets.** It fetches every object's ETag individually, which means one request per object and a runtime that grows linearly with bucket size — minutes on tens of thousands of objects, considerably worse beyond that. This is why `push` and `status` use mtime instead, and why `verify` is best treated as an occasional audit rather than something you run on every deploy.