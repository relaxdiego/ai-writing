# tug

`tug` pushes a local directory up to an S3-compatible bucket. It is deliberately one-way: local is the source of truth, the remote is a destination, and nothing ever travels back down. If you want a two-way sync, or a tool that mirrors deletions, `tug` is the wrong shape and you should reach for `rclone` or `aws s3 sync` instead.

The sync itself is cheap by default. Before uploading anything, `tug` compares each local file's size and modification time against the corresponding remote object and skips the ones that match, so a re-run over an unchanged tree costs little more than the listing calls. When mtimes are unreliable — after a checkout, a restore from backup, or a copy that didn't preserve timestamps — `tug verify` does the same comparison against checksums instead.

## Installation

With a Go toolchain:

```
go install github.com/yourorg/tug@latest
```

Or download a prebuilt binary from the releases page and put it somewhere on your `PATH`:

```
curl -sSL https://github.com/yourorg/tug/releases/latest/download/tug-linux-amd64 -o /usr/local/bin/tug
chmod +x /usr/local/bin/tug
```

## Credentials

`tug` looks for credentials in `~/.tug/credentials` first, falling back to the environment. The file is INI-style:

```ini
[default]
access_key_id = AKIAIOSFODNN7EXAMPLE
secret_access_key = wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
endpoint = https://s3.us-east-1.amazonaws.com
region = us-east-1
```

The equivalent environment variables are `TUG_ACCESS_KEY_ID`, `TUG_SECRET_ACCESS_KEY`, `TUG_ENDPOINT`, and `TUG_REGION`. Setting any of them overrides the corresponding value from the file, which makes it straightforward to keep a normal profile on disk and point a single CI run at a different bucket.

## Commands

`tug push` walks the local directory, compares against the remote, and uploads whatever differs. Pass `--dry-run` to print the plan without transferring anything — worth doing the first time you point `tug` at a new bucket, since a misconfigured prefix is much easier to notice in a listing than to undo afterwards.

```
tug push ./site s3://my-bucket/prod
tug push ./site s3://my-bucket/prod --dry-run
```

`tug status` reports what a push would do without performing one. It is the same comparison `push` runs internally, printed as a summary of new, changed, and unchanged files.

```
tug status ./site s3://my-bucket/prod
```

`tug verify` compares checksums rather than size and mtime. This is the command to reach for when you suspect a file was uploaded truncated or a timestamp lies about the contents, and it is the slow one — see the limitations below.

```
tug verify ./site s3://my-bucket/prod
```

## Ignoring files

Drop a `.tugignore` at the root of the directory you're pushing. It uses gitignore syntax, including negation with `!` and directory-only patterns with a trailing slash:

```
node_modules/
*.log
.DS_Store
!important.log
```

Only the root `.tugignore` is read; `tug` does not pick up nested ignore files the way git does.

## Limitations

There is no delete propagation. Removing a file locally leaves the remote object in place, so a bucket that has been pushed to for a long time will accumulate objects that no longer exist on disk, and you will need to prune them yourself.

Files larger than 5GB will fail to upload, because `tug` does not implement multipart upload and 5GB is the single-request ceiling in the S3 API. The failure is reported per-file and does not abort the rest of the push.

`tug verify` is slow on large buckets. It fetches every object's ETag to compare against a locally computed checksum, which means one request per object with no way to batch them, so verification time grows linearly with object count rather than with the number of files that actually changed. On a bucket of any real size, prefer `tug status` for routine checks and save `verify` for when you have a specific reason to distrust the mtimes.