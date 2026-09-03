# tug

`tug` pushes a local directory up to an S3-compatible bucket. It is deliberately one-way: local is the source of truth, the remote is a copy, and nothing that happens in the bucket ever comes back down to your disk. If you want two-way sync, conflict resolution, or a mirror that deletes remote files when you delete them locally, tug is the wrong tool and will quietly do the wrong thing for you.

## Installing

With a Go toolchain installed, `go install github.com/you/tug@latest` puts the binary on your `GOPATH/bin`. Otherwise grab a prebuilt binary from the releases page, drop it somewhere on your `PATH`, and make it executable. There are no runtime dependencies — it's a single static binary.

## Credentials

tug looks for `~/.tug/credentials` first, falling back to the environment if the file is missing. The file is a simple key-value list:

```
access_key_id = AKIAEXAMPLE
secret_access_key = wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
endpoint = https://s3.us-east-1.amazonaws.com
region = us-east-1
```

The environment equivalents are `TUG_ACCESS_KEY_ID`, `TUG_SECRET_ACCESS_KEY`, `TUG_ENDPOINT`, and `TUG_REGION`. Environment variables win over the file when both are present, which makes it easy to override a default profile for a single invocation without editing anything. Since the credentials file holds a secret in plaintext, tug refuses to read it if its permissions are broader than `0600`.

## Commands

`tug push <local-dir> <bucket>` walks the directory and uploads everything that differs from the remote. A file is considered unchanged — and therefore skipped — when its size and modification time both match the corresponding object. This comparison is cheap because it only needs the listing metadata, but it inherits the usual weakness of mtime-based sync: a file edited so that its size stays identical and its mtime is restored will be treated as already uploaded. Adding `--dry-run` prints the exact set of uploads and skips without touching the bucket, which is worth doing the first time you point tug at an unfamiliar prefix.

`tug status <local-dir> <bucket>` performs the same comparison and prints the result without uploading anything. It differs from `--dry-run` only in intent; use whichever reads better in your scripts.

`tug verify <local-dir> <bucket>` ignores mtimes entirely and compares checksums instead, so it catches the case where a file changed but its metadata didn't. Run it when you actually need to trust the copy — before decommissioning the local disk, say — rather than as part of a routine push.

## Ignoring files

If a `.tugignore` file exists at the root of the directory being pushed, tug reads it using gitignore syntax: one pattern per line, `#` for comments, `!` to negate an earlier pattern, and a trailing `/` to restrict a pattern to directories. Patterns are matched relative to the root, so the file behaves the way you'd expect coming from git. Only the root file is consulted — nested `.tugignore` files in subdirectories are not read.

## Limitations

There is no delete propagation. Removing a file locally leaves the object in the bucket forever, so a long-lived bucket accumulates everything you have ever pushed, and a "synced" bucket is really a superset of your local directory. Clean up manually if that matters.

Files over 5GB will fail to upload, because tug doesn't implement multipart upload and that's the single-request ceiling the S3 API imposes. The failure is loud rather than silent, but the only fix today is to split the file or use another tool for it.

`verify` is slow on large buckets. It fetches every object's ETag individually, so runtime scales with object count rather than with the number of files that actually changed — on a bucket with hundreds of thousands of objects this can take a long time and generate a correspondingly large number of API requests, which may cost real money depending on your provider. That's the reason mtime comparison is the default and `verify` is a separate command.