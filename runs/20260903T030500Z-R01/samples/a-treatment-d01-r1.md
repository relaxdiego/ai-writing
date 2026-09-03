# tug

One-way sync from a local directory to an S3-compatible bucket.

`tug push` walks a local directory, compares each file against the corresponding remote object, and uploads anything that differs. Files whose size and modification time already match the remote are skipped. Nothing is ever deleted or downloaded.

## Install

```
go install github.com/example/tug@latest
```

Or download a prebuilt binary for your platform from the releases page and put it somewhere on your `PATH`.

## Quick start

```
tug push ./site s3://my-bucket/site
```

Add `--dry-run` to see what would be uploaded without transferring anything:

```
tug push --dry-run ./site s3://my-bucket/site
```

## Commands

### `tug push <local-dir> <s3-uri>`

Uploads files that are new or changed. A file is considered unchanged when its size and mtime match the remote object's, so a push over an already-synced directory does almost no work.

| Flag | Description |
| --- | --- |
| `--dry-run` | List the planned uploads and exit without writing anything. |
| `--endpoint <url>` | S3-compatible endpoint. Defaults to AWS. |
| `--profile <name>` | Credentials profile to use. |
| `--ignore-file <path>` | Path to an ignore file. Defaults to `.tugignore` in the local directory. |

### `tug status <local-dir> <s3-uri>`

Reports what a push would do, grouped by new, changed, and unchanged. Read-only; it makes no writes and takes the same comparison shortcuts as `push`.

### `tug verify <local-dir> <s3-uri>`

Compares checksums instead of mtimes. Use it when you suspect a file was uploaded truncated or corrupted, or when mtimes have been rewritten by a tool that doesn't preserve them (`rsync` without `-t`, some CI checkouts). Slower than `status` — see Limitations.

## Credentials

`tug` looks for credentials in this order:

1. Environment variables: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, and optionally `AWS_SESSION_TOKEN`.
2. `~/.tug/credentials`.

The credentials file is INI-style, with one section per profile:

```ini
[default]
access_key_id = AKIAEXAMPLE
secret_access_key = wJalrEXAMPLEKEY
endpoint = https://s3.us-west-002.backblazeb2.com

[staging]
access_key_id = AKIAOTHER
secret_access_key = 7RtKEXAMPLEKEY
```

Select a non-default section with `--profile staging`. An `--endpoint` flag overrides the value in the file.

## Ignoring files

If a `.tugignore` file exists in the local directory, `tug` reads it and skips matching paths. The syntax is gitignore syntax — glob patterns, `!` negation, trailing `/` for directories, and `#` comments:

```
node_modules/
*.log
.DS_Store
!important.log
```

`.tugignore` applies to `push`, `status`, and `verify` alike, so ignored files are never reported as missing from the remote.

## Limitations

**No delete propagation.** Deleting a local file does not delete the remote object. Remote objects that no longer exist locally are left alone and are not reported. If you need the remote to shrink, remove those objects yourself.

**No multipart upload.** Files larger than 5 GB exceed the single-object PUT limit and will fail. Split them or upload them with another tool.

**`verify` is slow on large buckets.** It fetches every object's ETag individually, so runtime grows linearly with object count and it is dominated by round trips, not bandwidth. On a bucket with tens of thousands of objects, expect minutes. Prefer `status` for routine checks and reach for `verify` when you have a specific reason to distrust the mtimes.